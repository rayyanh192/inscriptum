/**
 * INSCRIPTUM - Self-Learning Email Assistant
 * Discord Bot Frontend
 * 
 * This bot is the gateway between the user and the self-learning agent.
 * 
 * INCOMING EMAILS:
 * - Notifies user about important emails
 * - Asks for feedback when uncertain
 * - Learns from user responses
 * 
 * OUTGOING EMAILS:
 * - Suggests when user should respond
 * - Generates drafts in user's style
 * - Sends via Gmail API
 */

import dotenv from 'dotenv';
import express from 'express';
import { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } from 'discord.js';
import Groq from 'groq-sdk';
import admin from 'firebase-admin';
import fs from 'fs';
import { sendEmail, replyToEmail } from './email-sender.js';

dotenv.config();

const app = express();
app.use(express.json());

// Initialize Firebase
const serviceAccount = JSON.parse(fs.readFileSync('./firebase-service-account.json'));
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });
}
const db = admin.firestore();

// Initialize Groq
const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

// Initialize Discord client
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
  partials: [Partials.Channel],
});

let botReady = false;
let notificationChannel = null;
let lastCheckedTimestamp = Date.now();

// Track pending decisions awaiting user feedback
const pendingDecisions = new Map();
// Track draft responses awaiting user approval
const pendingDrafts = new Map();

// ============================================================
// AGENT INTEGRATION - Call Python agent via Firebase
// ============================================================

/**
 * Process an email through the self-learning agent
 * Stores the decision in Firebase for the agent to process
 */
async function processEmailWithAgent(email) {
  // Get learned rules to make decision
  const rules = [];
  const rulesSnapshot = await db.collection('learned_rules')
    .where('status', '==', 'active')
    .get();
  
  rulesSnapshot.forEach(doc => rules.push(doc.to_dict ? doc.to_dict() : doc.data()));
  
  // Sort by specificity (more conditions = more specific)
  rules.sort((a, b) => {
    const aConditions = Object.keys(a.conditions || {}).length;
    const bConditions = Object.keys(b.conditions || {}).length;
    if (bConditions !== aConditions) return bConditions - aConditions;
    return (b.confidence || 0) - (a.confidence || 0);
  });

  // Check if any rule matches
  let matchedRule = null;
  for (const rule of rules) {
    if (ruleMatches(rule, email)) {
      matchedRule = rule;
      break;
    }
  }

  // If rule matched, use it
  if (matchedRule) {
    return {
      action: matchedRule.action,
      confidence: matchedRule.confidence || 0.8,
      reasoning: `Learned rule: ${matchedRule.pattern || matchedRule.description}`,
      learned_rule_id: matchedRule.id,
      is_learned: true
    };
  }

  // Otherwise, use LLM to decide
  const decision = await makeDecisionWithLLM(email);
  return decision;
}

/**
 * Check if a rule matches an email
 */
function ruleMatches(rule, email) {
  const conditions = rule.conditions || {};
  
  for (const [key, value] of Object.entries(conditions)) {
    if (key === 'sender_contains') {
      if (!email.from.toLowerCase().includes(value.toLowerCase())) return false;
    } else if (key === 'sender_domain') {
      const domain = email.from.split('@')[1] || '';
      if (domain !== value) return false;
    } else if (key === 'subject_contains') {
      if (!email.subject.toLowerCase().includes(value.toLowerCase())) return false;
    }
  }
  
  return Object.keys(conditions).length > 0; // Only match if has conditions
}

/**
 * Use LLM to make a decision when no learned rules apply
 */
async function makeDecisionWithLLM(email) {
  const prompt = `You are an email assistant. Analyze this email and decide what action to take.

Email:
- From: ${email.from}
- Subject: ${email.subject}
- Body: ${(email.body || '').slice(0, 500)}

Possible actions:
- "reply" - Important email that needs a response
- "star" - Important but doesn't need immediate response
- "archive" - Not important, can be archived
- "ignore" - Spam or irrelevant

Return JSON only:
{
  "action": "reply|star|archive|ignore",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "needs_user_input": true/false
}`;

  try {
    const completion = await groq.chat.completions.create({
      messages: [{ role: 'user', content: prompt }],
      model: 'llama-3.1-8b-instant',
      temperature: 0.3,
      max_tokens: 200,
    });

    const response = completion.choices[0]?.message?.content || '{}';
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
  } catch (error) {
    console.error('LLM decision error:', error);
  }

  return {
    action: 'star',
    confidence: 0.5,
    reasoning: 'Could not analyze, marked for review',
    needs_user_input: true
  };
}

/**
 * Record user feedback and trigger learning
 */
async function recordFeedback(decisionId, feedbackType, correctAction = null) {
  const feedbackDoc = {
    decision_id: decisionId,
    feedback_type: feedbackType,
    feedback_data: correctAction ? { correct_action: correctAction } : {},
    timestamp: admin.firestore.FieldValue.serverTimestamp()
  };

  await db.collection('training_feedback').add(feedbackDoc);

  // If user corrected the action, create a learned rule
  if (feedbackType === 'action_wrong' && correctAction) {
    const decision = pendingDecisions.get(decisionId);
    if (decision && decision.email) {
      const email = decision.email;
      const ruleId = `rule_discord_${Date.now()}`;
      
      // Extract sender identifier
      const senderPart = email.from.split('@')[0].toLowerCase();
      
      await db.collection('learned_rules').doc(ruleId).set({
        id: ruleId,
        pattern: `Emails from ${email.from.slice(0, 30)}... should be ${correctAction}`,
        description: `Learned from Discord feedback`,
        conditions: {
          sender_contains: senderPart
        },
        action: correctAction,
        confidence: 0.95,
        created_from: 'discord_feedback',
        decision_id: decisionId,
        created_at: new Date().toISOString(),
        status: 'active'
      });

      console.log(`📚 Created learned rule: ${ruleId}`);
    }
  }

  pendingDecisions.delete(decisionId);
}

// ============================================================
// EMAIL MONITORING
// ============================================================

async function checkForNewEmails() {
  try {
    // Get agent decisions that need user notification
    const snapshot = await db.collection('agent_decisions')
      .where('notified', '==', false)
      .orderBy('timestamp', 'desc')
      .limit(5)
      .get();

    if (snapshot.empty) {
      // Also check for new unprocessed emails
      await checkForUnprocessedEmails();
      return;
    }

    for (const doc of snapshot.docs) {
      const decision = doc.data();
      await notifyUserAboutEmail(doc.id, decision);
      
      // Mark as notified
      await doc.ref.update({ notified: true });
    }
  } catch (error) {
    // Fallback: check emails directly
    await checkForUnprocessedEmails();
  }
}

async function checkForUnprocessedEmails() {
  try {
    const snapshot = await db.collection('emails')
      .where('discord_notified', '!=', true)
      .orderBy('discord_notified')
      .orderBy('timestamp', 'desc')
      .limit(3)
      .get();

    if (snapshot.empty) return;

    for (const doc of snapshot.docs) {
      const email = { id: doc.id, ...doc.data() };
      
      // Process through agent
      const decision = await processEmailWithAgent(email);
      
      // Store decision
      const decisionId = `decision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      await db.collection('agent_decisions').doc(decisionId).set({
        ...decision,
        email_id: email.id,
        sender: email.from,
        subject: email.subject,
        timestamp: new Date().toISOString(),
        notified: false
      });

      // Notify user
      await notifyUserAboutEmail(decisionId, { ...decision, email });
      
      // Mark email as notified
      await doc.ref.update({ discord_notified: true });
    }
  } catch (error) {
    console.error('Error checking unprocessed emails:', error.message);
  }
}

// ============================================================
// DISCORD NOTIFICATIONS
// ============================================================

async function notifyUserAboutEmail(decisionId, decision) {
  if (!notificationChannel) return;

  const email = decision.email || {};
  const action = decision.action || 'review';
  const confidence = decision.confidence || 0.5;

  // Store for feedback tracking
  pendingDecisions.set(decisionId, { decision, email });

  // Color based on action
  const colors = {
    reply: 0xFF6B6B,    // Red - needs response
    star: 0xFFE66D,     // Yellow - important
    archive: 0x4ECDC4,  // Teal - can archive
    ignore: 0x95A5A6    // Gray - spam
  };

  const embed = new EmbedBuilder()
    .setColor(colors[action] || 0x7289DA)
    .setTitle(`📧 ${email.subject || 'New Email'}`)
    .addFields(
      { name: 'From', value: email.from || 'Unknown', inline: true },
      { name: 'Action', value: action.toUpperCase(), inline: true },
      { name: 'Confidence', value: `${Math.round(confidence * 100)}%`, inline: true }
    )
    .setDescription(decision.reasoning || 'No reasoning provided')
    .setTimestamp();

  // Low confidence = ask user
  if (confidence < 0.7) {
    embed.setFooter({ text: '⚠️ Low confidence - please verify' });
  }

  // Build action buttons
  const row = new ActionRowBuilder();

  if (action === 'reply') {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(`draft_${decisionId}`)
        .setLabel('📝 Draft Response')
        .setStyle(ButtonStyle.Primary),
      new ButtonBuilder()
        .setCustomId(`correct_${decisionId}`)
        .setLabel('✏️ Wrong Action')
        .setStyle(ButtonStyle.Secondary),
      new ButtonBuilder()
        .setCustomId(`confirm_${decisionId}`)
        .setLabel('✅ Correct')
        .setStyle(ButtonStyle.Success)
    );
  } else {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(`confirm_${decisionId}`)
        .setLabel('✅ Correct')
        .setStyle(ButtonStyle.Success),
      new ButtonBuilder()
        .setCustomId(`should_reply_${decisionId}`)
        .setLabel('📩 Should Reply')
        .setStyle(ButtonStyle.Primary),
      new ButtonBuilder()
        .setCustomId(`correct_${decisionId}`)
        .setLabel('✏️ Change Action')
        .setStyle(ButtonStyle.Secondary)
    );
  }

  await notificationChannel.send({ embeds: [embed], components: [row] });
}

// ============================================================
// RESPONSE GENERATION
// ============================================================

async function generateDraftResponse(email) {
  // Get user's recent sent emails to learn style
  const sentEmails = await db.collection('emails')
    .where('is_sent', '==', true)
    .orderBy('timestamp', 'desc')
    .limit(5)
    .get();

  let styleContext = '';
  sentEmails.forEach(doc => {
    const sent = doc.data();
    styleContext += `\nExample sent email:\nSubject: ${sent.subject}\nBody: ${sent.body?.slice(0, 200)}\n`;
  });

  const prompt = `You are helping draft an email response. Match the user's writing style based on their recent emails.

${styleContext}

Now draft a response to this email:
From: ${email.from}
Subject: ${email.subject}
Body: ${(email.body || '').slice(0, 500)}

Write a natural, concise response that sounds like the user wrote it. Keep it brief and professional.
Just write the email body, no subject line needed.`;

  try {
    const completion = await groq.chat.completions.create({
      messages: [{ role: 'user', content: prompt }],
      model: 'llama-3.1-8b-instant',
      temperature: 0.7,
      max_tokens: 300,
    });

    return completion.choices[0]?.message?.content || 'Unable to generate draft';
  } catch (error) {
    console.error('Draft generation error:', error);
    return 'Unable to generate draft. Please try again.';
  }
}

// ============================================================
// BUTTON INTERACTIONS
// ============================================================

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  const [action, decisionId] = interaction.customId.split('_').reduce((acc, part, i, arr) => {
    if (i === 0) return [part, ''];
    return [acc[0], acc[1] + (acc[1] ? '_' : '') + part];
  }, ['', '']);

  const pending = pendingDecisions.get(decisionId);

  try {
    // ---- CONFIRM CORRECT ----
    if (interaction.customId.startsWith('confirm_')) {
      await recordFeedback(decisionId, 'action_correct');
      await interaction.reply({ content: '✅ Got it! I\'ll remember this for similar emails.', ephemeral: true });
    }

    // ---- DRAFT RESPONSE ----
    else if (interaction.customId.startsWith('draft_')) {
      await interaction.deferReply();
      
      if (!pending || !pending.email) {
        await interaction.editReply('❌ Could not find the email. It may have expired.');
        return;
      }

      const draft = await generateDraftResponse(pending.email);
      
      // Store draft for sending
      const draftId = `draft_${Date.now()}`;
      pendingDrafts.set(draftId, { email: pending.email, draft, decisionId });

      const embed = new EmbedBuilder()
        .setColor(0x7289DA)
        .setTitle('📝 Draft Response')
        .setDescription(draft)
        .addFields({ name: 'To', value: pending.email.from, inline: true })
        .setFooter({ text: 'Review and send, or edit as needed' });

      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`send_${draftId}`)
          .setLabel('📤 Send')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId(`edit_${draftId}`)
          .setLabel('✏️ Edit')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId(`discard_${draftId}`)
          .setLabel('🗑️ Discard')
          .setStyle(ButtonStyle.Danger)
      );

      await interaction.editReply({ embeds: [embed], components: [row] });
    }

    // ---- SEND EMAIL ----
    else if (interaction.customId.startsWith('send_')) {
      const draftId = interaction.customId.replace('send_', '');
      const draftData = pendingDrafts.get(draftId);

      if (!draftData) {
        await interaction.reply({ content: '❌ Draft expired. Please generate a new one.', ephemeral: true });
        return;
      }

      await interaction.deferReply();

      const result = await replyToEmail(draftData.email, draftData.draft);

      if (result.success) {
        await interaction.editReply('✅ Email sent successfully!');
        await recordFeedback(draftData.decisionId, 'response_used');
        pendingDrafts.delete(draftId);
      } else {
        await interaction.editReply(`❌ Failed to send: ${result.error}`);
      }
    }

    // ---- DISCARD DRAFT ----
    else if (interaction.customId.startsWith('discard_')) {
      const draftId = interaction.customId.replace('discard_', '');
      pendingDrafts.delete(draftId);
      await interaction.reply({ content: '🗑️ Draft discarded.', ephemeral: true });
    }

    // ---- SHOULD REPLY ----
    else if (interaction.customId.startsWith('should_reply_')) {
      await recordFeedback(decisionId, 'action_wrong', 'reply');
      await interaction.reply({ 
        content: '📝 Got it! I\'ll suggest replying to similar emails in the future.\nWould you like me to draft a response?',
        ephemeral: true 
      });
    }

    // ---- CORRECT/CHANGE ACTION ----
    else if (interaction.customId.startsWith('correct_')) {
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`setaction_reply_${decisionId}`)
          .setLabel('Reply')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId(`setaction_star_${decisionId}`)
          .setLabel('Star')
          .setStyle(ButtonStyle.Secondary),
        new ButtonBuilder()
          .setCustomId(`setaction_archive_${decisionId}`)
          .setLabel('Archive')
          .setStyle(ButtonStyle.Secondary),
        new ButtonBuilder()
          .setCustomId(`setaction_ignore_${decisionId}`)
          .setLabel('Ignore')
          .setStyle(ButtonStyle.Secondary)
      );

      await interaction.reply({ 
        content: 'What should the correct action be?', 
        components: [row],
        ephemeral: true 
      });
    }

    // ---- SET CORRECT ACTION ----
    else if (interaction.customId.startsWith('setaction_')) {
      const parts = interaction.customId.split('_');
      const correctAction = parts[1];
      const decId = parts.slice(2).join('_');

      await recordFeedback(decId, 'action_wrong', correctAction);
      await interaction.reply({ 
        content: `✅ Thanks! I\'ll ${correctAction} similar emails in the future.`,
        ephemeral: true 
      });
    }

  } catch (error) {
    console.error('Button interaction error:', error);
    if (!interaction.replied && !interaction.deferred) {
      await interaction.reply({ content: '❌ Something went wrong. Please try again.', ephemeral: true });
    }
  }
});

// ============================================================
// MESSAGE HANDLING (Chat)
// ============================================================

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (message.channel.id !== process.env.DISCORD_CHANNEL_ID) return;

  // Show typing
  await message.channel.sendTyping();

  // Simple chat - can expand later
  try {
    const completion = await groq.chat.completions.create({
      messages: [
        { role: 'system', content: 'You are Inscriptum, a helpful email assistant. Keep responses brief and friendly.' },
        { role: 'user', content: message.content }
      ],
      model: 'llama-3.1-8b-instant',
      temperature: 0.7,
      max_tokens: 300,
    });

    const response = completion.choices[0]?.message?.content || "Sorry, I couldn't process that.";
    await message.reply(response);
  } catch (error) {
    console.error('Chat error:', error);
    await message.reply("Sorry, I'm having trouble right now. Try again?");
  }
});

// ============================================================
// STARTUP
// ============================================================

client.once('ready', async () => {
  console.log(`🤖 Discord bot logged in as ${client.user.tag}`);
  botReady = true;

  notificationChannel = client.channels.cache.get(process.env.DISCORD_CHANNEL_ID);
  if (notificationChannel) {
    console.log(`📢 Notification channel: #${notificationChannel.name}`);
    
    await notificationChannel.send({
      embeds: [
        new EmbedBuilder()
          .setColor(0x7289DA)
          .setTitle('🚀 Inscriptum Online')
          .setDescription('Self-learning email assistant ready!\n\n• I\'ll notify you about important emails\n• Ask for feedback to improve\n• Draft responses in your style')
          .setTimestamp()
      ]
    });

    // Start monitoring
    console.log('🔄 Starting email monitoring...');
    setInterval(checkForNewEmails, 10000); // Check every 10 seconds
  } else {
    console.error('❌ Could not find notification channel!');
  }
});

// Health check endpoint
app.get('/', (req, res) => {
  res.json({
    status: 'running',
    botReady,
    channel: notificationChannel?.name || 'not connected',
    pendingDecisions: pendingDecisions.size,
    pendingDrafts: pendingDrafts.size
  });
});

app.listen(process.env.PORT || 3000, () => {
  console.log(`🌐 Server running on port ${process.env.PORT || 3000}`);
});

client.login(process.env.DISCORD_BOT_TOKEN);
