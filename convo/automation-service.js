import { Stagehand } from '@browserbasehq/stagehand';
import { z } from 'zod';

const DEFAULT_MODEL_NAME = process.env.STAGEHAND_MODEL || 'openai/gpt-4o';

function resolveModelConfig(modelName) {
  const normalized = modelName || 'openai/gpt-4o';
  const provider = normalized.includes('/')
    ? normalized.split('/')[0]
    : normalized.startsWith('groq-')
      ? 'groq'
      : normalized.startsWith('claude-')
        ? 'anthropic'
        : normalized.startsWith('gpt-') || normalized.startsWith('o1') || normalized.startsWith('o3')
          ? 'openai'
          : null;

  let apiKey = null;
  if (provider === 'groq') apiKey = process.env.GROQ_API_KEY;
  else if (provider === 'anthropic') apiKey = process.env.ANTHROPIC_API_KEY;
  else if (provider === 'openai') apiKey = process.env.OPENAI_API_KEY;
  else if (provider === 'google') apiKey = process.env.GOOGLE_API_KEY;
  else apiKey = process.env.OPENAI_API_KEY || process.env.ANTHROPIC_API_KEY || process.env.GROQ_API_KEY;

  return { modelName: normalized, apiKey };
}

const FIELD_LABELS = {
  first_name: ['first name', 'given name'],
  last_name: ['last name', 'surname', 'family name'],
  full_name: ['full name', 'name'],
  email: ['email', 'email address'],
  phone: ['phone', 'mobile', 'cell'],
  confirmation_number: ['confirmation number', 'record locator', 'pnr', 'booking reference'],
  booking_reference: ['booking reference', 'reservation code'],
  date_of_birth: ['date of birth', 'dob', 'birth date'],
  zip: ['zip', 'postal code'],
  address: ['address', 'street address'],
  city: ['city', 'town'],
  state: ['state', 'province'],
  country: ['country'],
  last4_ssn: ['last 4 ssn', 'ssn last 4', 'last 4 of ssn'],
};

const REQUIRED_FIELDS_SCHEMA = z.object({
  fields: z.array(
    z.object({
      label: z.string().optional(),
      placeholder: z.string().optional(),
      name: z.string().optional(),
      type: z.string().optional(),
      question: z.string().optional(),
      suggested_key: z.string().optional(),
    })
  ).default([])
});

function normalizeKey(value) {
  return (value || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function pickFieldKey(field) {
  return (
    normalizeKey(field.suggested_key) ||
    normalizeKey(field.label) ||
    normalizeKey(field.placeholder) ||
    normalizeKey(field.name) ||
    'unknown'
  );
}

function formatQuestion(field) {
  if (field.question) return field.question;
  const label = field.label || field.placeholder || field.name || 'this field';
  return `What should I enter for "${label}"?`;
}

export async function initAutomationSession({ sessionId } = {}) {
  const modelConfig = resolveModelConfig(DEFAULT_MODEL_NAME);
  const stagehand = new Stagehand({
    env: 'BROWSERBASE',
    apiKey: process.env.BROWSERBASE_API_KEY,
    projectId: process.env.BROWSERBASE_PROJECT_ID,
    browserbaseSessionID: sessionId,
    model: {
      modelName: modelConfig.modelName,
      apiKey: modelConfig.apiKey,
    },
    verbose: 0,
  });

  await stagehand.init();
  const page = stagehand.context.pages()[0];

  return {
    stagehand,
    page,
    sessionId: stagehand.browserbaseSessionID,
    sessionUrl: stagehand.browserbaseSessionURL,
    debugUrl: stagehand.browserbaseDebugURL,
  };
}

export async function fillKnownFields(stagehand, context = {}) {
  const entries = Object.entries(context).filter(([, value]) => value !== undefined && value !== null && `${value}`.trim() !== '');

  for (const [key, value] of entries) {
    const labels = FIELD_LABELS[key] || [key.replace(/_/g, ' ')];
    for (const label of labels) {
      try {
        const normalizedLabel = label.toLowerCase();
        const stringValue = String(value);
        if (stringValue.includes('@') && !normalizedLabel.includes('email')) {
          continue;
        }
        if (/(confirmation|booking|reference|pnr|record locator|ssn|zip|postal|phone|mobile|cell|dob|birth)/i.test(normalizedLabel)) {
          const hasDigit = /\d/.test(stringValue);
          if (!hasDigit) continue;
        }
        await stagehand.act(`fill the ${label} field with %value%`, {
          variables: { value: String(value) },
        });
        break;
      } catch (error) {
        continue;
      }
    }
  }
}

export async function findMissingFields(stagehand) {
  const result = await stagehand.extract(
    'Find all required or empty input fields that still need user input on this page. Ignore fields that are already filled. For each, return label, placeholder, name, type, a suggested key name, and a short question to ask the user.',
    REQUIRED_FIELDS_SCHEMA
  );

  const fields = result?.fields || [];
  return fields.map(field => ({
    ...field,
    key: pickFieldKey(field),
    question: formatQuestion(field),
  }));
}

export async function attemptSubmit(stagehand) {
  try {
    const stillMissing = await findMissingFields(stagehand);
    if (stillMissing.length > 0) {
      return false;
    }
  } catch (error) {
    // If we can't detect fields, fall through and try submit anyway.
  }
  try {
    await stagehand.act('click the primary submit, confirm, finish, or continue button if available');
    await stagehand.act('wait for any confirmation or success message to load');
  } catch (error) {
    return false;
  }
  return true;
}

export async function summarizeCompletion(stagehand) {
  try {
    const result = await stagehand.extract(
      'Summarize any confirmation message, success state, or reference number visible on the page.',
      z.object({
        summary: z.string().optional(),
        reference: z.string().optional(),
      })
    );
    return result;
  } catch (error) {
    return { summary: 'Completed automation. No confirmation text detected.' };
  }
}
