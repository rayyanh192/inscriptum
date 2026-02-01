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
import { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder, ModalBuilder, TextInputBuilder, TextInputStyle } from 'discord.js';
import Groq from 'groq-sdk';
import admin from 'firebase-admin';
import fs from 'fs';
import { sendEmail, replyToEmail } from './email-sender.js';
import { fetchEmails } from './scraper.js';

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

// Track pending decisions awaiting user feedback (with expiry)
const pendingDecisions = new Map();
const DECISION_EXPIRY_MS = 5 * 60 * 1000; // Keep decisions for 5 minutes
// Track draft responses awaiting user approval
const pendingDrafts = new Map();
// Conversation history per user (keeps context)
const conversationHistory = new Map();
// Cache of recent email search results
const emailSearchCache = new Map();
// Prevent duplicate message processing
const processedMessages = new Set();

const MAX_HISTORY_LENGTH = 20; // Keep last 20 messages per user

// ============================================================
// AGENT INTEGRATION - Call Python agent via Firebase
// ============================================================

/**
 * Process an email through the self-learning agent
 * Stores the decision in Firebase for the agent to process
 */
async function processEmailWithAgent(email) {
  // Try to use Python agent server first
  try {
    const response = await fetch('http://localhost:5001/process-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(email)
    });
    
    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success') {
        console.log('  🐍 Using Python agent');
        return result.decision;
      }
    }
  } catch (error) {
    console.log('  ⚠️ Python agent unavailable, falling back to local logic');
  }
  
  // Fallback: Use local learned rules + LLM
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
  const from = (email.from || '').toLowerCase();
  const subject = (email.subject || '').toLowerCase();
  const body = (email.body || '').toLowerCase();
  const combinedText = `${subject} ${body}`.slice(0, 200);
  
  for (const [key, value] of Object.entries(conditions)) {
    if (key === 'sender_contains') {
      if (!from.includes((value || '').toLowerCase())) return false;
    } else if (key === 'sender_domain') {
      const domain = from.split('@')[1] || '';
      if (domain !== value) return false;
    } else if (key === 'subject_contains') {
      if (!subject.includes((value || '').toLowerCase())) return false;
    } else if (key === 'content_pattern') {
      // Special pattern matching for casual greetings
      if (value === 'casual_greeting') {
        const casualPatterns = ['what up', 'whats up', 'wassup', 'sup', 'hey', 'hi ', 'hello', 'yo ', 'hiii'];
        const hasCasualPattern = casualPatterns.some(p => combinedText.includes(p));
        if (!hasCasualPattern) return false;
      }
    } else if (key === 'max_length') {
      // Check combined text length
      if (combinedText.length > value) return false;
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

Analyze for:
1. URGENCY: Is this time-sensitive? (dinner tonight, meeting soon, payment due, deadline, ASAP, urgent)
2. IMPORTANCE: Does this require immediate attention?

Possible actions:
- "reply" - Important email that needs a response (especially if urgent/time-sensitive)
- "star" - Important but doesn't need immediate response
- "archive" - Not important, can be archived
- "ignore" - Spam or irrelevant

Return JSON only:
{
  "action": "reply|star|archive|ignore",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "is_urgent": true/false,
  "is_time_sensitive": true/false,
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
      
      // Extract patterns from email
      const senderPart = email.from.split('@')[0].toLowerCase();
      const subject = (email.subject || '').toLowerCase();
      const body = (email.body || '').toLowerCase();
      const combinedText = `${subject} ${body}`.slice(0, 200);
      
      // Detect casual/short messages (high priority patterns)
      const casualPatterns = ['what up', 'whats up', 'wassup', 'sup', 'hey', 'hi ', 'hello', 'yo ', 'hiii'];
      const isCasualGreeting = casualPatterns.some(p => combinedText.includes(p)) && combinedText.length < 100;
      
      // Build conditions based on message characteristics
      const conditions = { sender_contains: senderPart };
      let pattern = `Emails from ${email.from.slice(0, 30)}...`;
      
      // If it's a casual greeting that should be ignored, make it very specific
      if (isCasualGreeting && correctAction === 'ignore') {
        conditions.content_pattern = 'casual_greeting';
        conditions.max_length = 100;
        pattern = `Casual short messages (${combinedText.slice(0, 30)}...) from ${email.from.slice(0, 20)}... → ${correctAction}`;
        console.log(`  📝 Creating SPECIFIC rule for casual messages`);
      } else if (subject.length > 5) {
        // Use subject pattern for more specific matching
        conditions.subject_contains = subject.slice(0, 30);
        pattern = `"${subject.slice(0, 30)}..." from ${email.from.slice(0, 20)}... → ${correctAction}`;
      }
      
      await db.collection('learned_rules').doc(ruleId).set({
        id: ruleId,
        pattern: pattern,
        description: `Learned from Discord feedback`,
        conditions: conditions,
        action: correctAction,
        confidence: 0.95,
        created_from: 'discord_feedback',
        decision_id: decisionId,
        created_at: new Date().toISOString(),
        status: 'active'
      });

      console.log(`📚 Created learned rule: ${ruleId} → ${correctAction}`);
    }
  }

  // Don't delete immediately - let it expire naturally after 5 minutes
  // pendingDecisions.delete(decisionId);
}

// ============================================================
// CONTINUOUS EMAIL SCRAPING & AGENT TRAINING
// ============================================================

let lastScrapeTime = 0;
const SCRAPE_INTERVAL = 5000; // Scrape every 5 seconds (for testing)

/**
 * Clean up expired decisions from memory
 * Runs periodically to prevent memory leaks
 */
function cleanupExpiredDecisions() {
  const now = Date.now();
  let cleaned = 0;
  
  for (const [id, data] of pendingDecisions.entries()) {
    if (data.expiresAt && data.expiresAt < now) {
      pendingDecisions.delete(id);
      cleaned++;
    }
  }
  
  if (cleaned > 0) {
    console.log(`🧹 Cleaned up ${cleaned} expired decision(s)`);
  }
}

// Run cleanup every minute
setInterval(cleanupExpiredDecisions, 60000);

/**
 * Scrape new emails from Gmail and add to Firebase
 * This runs every 5 seconds to keep the database up to date
 */
async function scrapeNewEmails() {
  const now = Date.now();
  if (now - lastScrapeTime < SCRAPE_INTERVAL) return;
  lastScrapeTime = now;

  console.log('📥 Scraping new emails from Gmail...');
  
  try {
    const emails = await fetchEmails(20); // Fetch last 20 emails
    console.log(`📧 Found ${emails.length} emails`);
    let newCount = 0;
    let updatedCount = 0;

    for (const email of emails) {
      const docRef = db.collection('emails').doc(email.id);
      const existing = await docRef.get();

      if (!existing.exists) {
        // New email - add it
        await docRef.set({
          ...email,
          discord_notified: false,
          agent_processed: false,
          scraped_at: admin.firestore.FieldValue.serverTimestamp()
        });
        newCount++;
        const sender = email.is_sent ? `TO: ${email.to}` : `FROM: ${email.from}`;
        console.log(`  ✅ New email: "${(email.subject || '').slice(0, 30)}..." ${sender.slice(0, 40)}`);
        
        // ADD THE SENDER TO PEOPLE COLLECTION (only for received emails)
        if (email.from && !email.is_sent) {
          await addPersonFromEmail(email.from, 'received_email');
        }
        // Add recipient for sent emails
        if (email.to && email.is_sent) {
          await addPersonFromEmail(email.to, 'sent_email');
        }
        
        // Check if this new email should trigger a notification
        console.log(`  🔍 Checking if email should be notified...`);
        try {
          // Process THIS specific email immediately instead of querying all recent ones
          await checkAndNotifyEmail(email.id);
        } catch (error) {
          console.error(`  ❌ Error checking email for notification:`, error.message);
        }
      } else {
        // Email exists - update behavior signals (read/starred/archived status may have changed)
        const existingData = existing.data();
        const changed = (
          existingData.is_read !== email.is_read ||
          existingData.is_starred !== email.is_starred ||
          existingData.is_archived !== email.is_archived ||
          existingData.is_deleted !== email.is_deleted ||
          existingData.has_reply !== email.has_reply
        );

        if (changed) {
          await docRef.update({
            is_read: email.is_read,
            is_starred: email.is_starred,
            is_archived: email.is_archived,
            is_deleted: email.is_deleted,
            has_reply: email.has_reply,
            labels: email.labels,
            last_synced: Date.now()
          });
          updatedCount++;
          console.log(`  🔄 Updated: "${(email.subject || '').slice(0, 40)}..."`);
          
          // Record this as implicit feedback for training
          await recordImplicitFeedback(email, existingData);
        }
      }
    }

    if (newCount > 0 || updatedCount > 0) {
      console.log(`✅ Scraped: ${newCount} new, ${updatedCount} updated`);
    } else {
      console.log(`   (no changes)`);
    }
  } catch (error) {
    console.error('❌ Scrape error:', error.message);
  }
}

/**
 * Add a person to the people collection from an email address
 */
async function addPersonFromEmail(emailAddress, source) {
  if (!emailAddress) return;
  
  // Extract email from "Name <email@domain.com>" format
  const emailMatch = emailAddress.match(/<([^>]+)>/) || [null, emailAddress];
  const cleanEmail = (emailMatch[1] || emailAddress).toLowerCase().trim();
  
  // Create a safe document ID
  const personKey = cleanEmail.replace(/[^a-z0-9@._-]/g, '').slice(0, 100);
  if (!personKey || personKey.length < 5) return;
  
  const personRef = db.collection('people').doc(personKey);
  const personDoc = await personRef.get();
  
  if (!personDoc.exists) {
    // Extract name from "Name <email>" format
    const nameMatch = emailAddress.match(/^([^<]+)</);
    const name = nameMatch ? nameMatch[1].trim() : cleanEmail.split('@')[0].replace(/[._]/g, ' ');
    
    await personRef.set({
      email: cleanEmail,
      name: name,
      importance_score: 0.5, // Start neutral
      email_count: 1,
      created_at: new Date().toISOString(),
      created_from: source,
      last_email_at: new Date().toISOString()
    });
    console.log(`👤 Added person: ${cleanEmail}`);
  }
  // Skip updating existing people to reduce quota usage
}

/**
 * Record implicit feedback when user takes action on email
 * This is how the agent learns from actual user behavior
 */
async function recordImplicitFeedback(newState, oldState) {
  const changes = [];
  
  // User read the email
  if (!oldState.is_read && newState.is_read) {
    changes.push({ signal: 'read', importance: 0.3 });
  }
  
  // User starred the email (strong signal - important!)
  if (!oldState.is_starred && newState.is_starred) {
    changes.push({ signal: 'starred', importance: 0.9 });
  }
  
  // User unstarred (was important, now not)
  if (oldState.is_starred && !newState.is_starred) {
    changes.push({ signal: 'unstarred', importance: -0.5 });
  }
  
  // User archived (handled, not important to keep in inbox)
  if (!oldState.is_archived && newState.is_archived) {
    changes.push({ signal: 'archived', importance: 0.2 });
  }
  
  // User deleted (spam or unwanted)
  if (!oldState.is_deleted && newState.is_deleted) {
    changes.push({ signal: 'deleted', importance: -0.8 });
  }
  
  // User replied (very important email!)
  if (!oldState.has_reply && newState.has_reply) {
    changes.push({ signal: 'replied', importance: 1.0 });
  }

  // Save implicit feedback for each change AND update person importance
  for (const change of changes) {
    await db.collection('training_feedback').add({
      email_id: newState.id,
      feedback_type: 'implicit_behavior',
      signal: change.signal,
      importance_score: change.importance,
      sender: newState.from || 'unknown',
      subject: newState.subject || '',
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });
    
    console.log(`📊 Recorded implicit feedback: ${change.signal} for ${(newState.subject || '').slice(0, 30)}...`);
    
    // DIRECTLY update person importance in the agent's people collection
    await updatePersonImportance(newState.from, change.signal);
  }

  // If user starred or replied, create/update a learned rule
  if (changes.some(c => c.signal === 'starred' || c.signal === 'replied')) {
    await createLearnedRuleFromBehavior(newState, 'reply');
  }
  
  // If user deleted, learn to ignore similar emails
  if (changes.some(c => c.signal === 'deleted')) {
    await createLearnedRuleFromBehavior(newState, 'ignore');
  }
}

/**
 * Update person importance score based on user behavior
 * This feeds directly into the agent's decision making
 */
async function updatePersonImportance(sender, signal) {
  if (!sender) return;
  
  const senderKey = sender.split('@')[0].toLowerCase().replace(/[^a-z0-9_]/g, '').slice(0, 50);
  if (!senderKey || senderKey.length < 2) return;
  
  const personRef = db.collection('people').doc(senderKey);
  const personDoc = await personRef.get();
  
  // Calculate importance adjustment based on signal
  const adjustments = {
    'starred': 0.15,
    'replied': 0.2,
    'read': 0.02,
    'archived': 0.0,
    'deleted': -0.25,
    'unstarred': -0.1
  };
  const adjustment = adjustments[signal] || 0;
  
  if (personDoc.exists) {
    const person = personDoc.data();
    const currentImportance = person.importance_score || 0.5;
    const newImportance = Math.max(0, Math.min(1, currentImportance + adjustment));
    
    await personRef.update({
      importance_score: newImportance,
      [`behavior_${signal}_count`]: admin.firestore.FieldValue.increment(1),
      last_behavior_update: new Date().toISOString()
    });
    
    console.log(`👤 Updated ${senderKey} importance: ${currentImportance.toFixed(2)} → ${newImportance.toFixed(2)}`);
  } else {
    // Create new person record
    const initialImportance = signal === 'starred' || signal === 'replied' ? 0.7 
      : signal === 'deleted' ? 0.2 
      : 0.5;
    
    await personRef.set({
      email: sender,
      name: sender.split('@')[0].replace(/[._]/g, ' '),
      importance_score: initialImportance,
      [`behavior_${signal}_count`]: 1,
      created_at: new Date().toISOString(),
      created_from: 'implicit_behavior'
    });
    
    console.log(`👤 Created person ${senderKey} with importance ${initialImportance}`);
  }
}

/**
 * Create a learned rule from user behavior
 */
async function createLearnedRuleFromBehavior(email, action) {
  const from = email.from || '';
  const senderPart = from.split('@')[0].toLowerCase().replace(/[^a-z0-9]/g, '');
  
  if (!senderPart || senderPart.length < 3) return;
  
  const ruleId = `rule_behavior_${senderPart}_${Date.now()}`;
  
  // Check if similar rule exists
  const existingRules = await db.collection('learned_rules')
    .where('conditions.sender_contains', '==', senderPart)
    .limit(1)
    .get();
  
  if (!existingRules.empty) {
    // Update confidence of existing rule
    const existingRule = existingRules.docs[0];
    const currentConfidence = existingRule.data().confidence || 0.8;
    await existingRule.ref.update({
      confidence: Math.min(0.99, currentConfidence + 0.05),
      reinforced_at: new Date().toISOString(),
      reinforcement_count: admin.firestore.FieldValue.increment(1)
    });
    console.log(`📈 Reinforced rule for ${senderPart}`);
    return;
  }
  
  // Create new rule
  await db.collection('learned_rules').doc(ruleId).set({
    id: ruleId,
    pattern: `Emails from ${from.slice(0, 40)} should be ${action}`,
    description: `Learned from user ${action === 'reply' ? 'starring/replying' : 'deleting'}`,
    conditions: {
      sender_contains: senderPart
    },
    action: action,
    confidence: 0.75,
    created_from: 'implicit_behavior',
    created_at: new Date().toISOString(),
    status: 'active'
  });
  
  console.log(`📚 Created behavior rule: ${action} emails from ${senderPart}`);
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

/**
 * Check and notify for a specific email by ID
 */
async function checkAndNotifyEmail(emailId) {
  try {
    console.log(`  📋 Processing email: ${emailId}`);
    const docRef = db.collection('emails').doc(emailId);
    const doc = await docRef.get();
    
    if (!doc.exists) {
      console.log(`  ❌ Email not found in database`);
      return;
    }
    
    const email = { id: doc.id, ...doc.data() };
    
    // Skip if already notified
    if (email.discord_notified === true) {
      console.log(`  ⏩ Already notified`);
      return;
    }
    
    // Skip SENT emails - only notify about received emails
    const isSent = email.is_sent || (!email.from && email.to);
    if (isSent) {
      await docRef.update({ discord_notified: true });
      console.log(`  ⏩ Skipped: sent email`);
      return;
    }
    
    console.log(`  🤖 Processing with agent: "${(email.subject || '').slice(0, 40)}..."`);
    
    // Process through agent
    const decision = await processEmailWithAgent(email);
    
    console.log(`  ✅ Agent decision: ${decision.action}, urgent: ${decision.is_urgent}, time-sensitive: ${decision.is_time_sensitive}`);
    
    // PRIORITY NOTIFICATION LOGIC
    const isUrgent = decision.is_urgent || decision.is_time_sensitive;
    const isHighConfidence = decision.confidence && decision.confidence > 0.7;
    
    // For reply/star actions: only notify if high confidence OR urgent
    // This prevents "pay me next month no rush" (low conf, not urgent) from notifying
    const isImportant = (decision.action === 'reply' || decision.action === 'star') && 
                        (isHighConfidence || isUrgent);
    
    const shouldNotify = isUrgent || isImportant;
    
    if (!shouldNotify) {
      await docRef.update({ discord_notified: true });
      console.log(`  ⏩ Skipped notification: not important enough`);
      return;
    }
    
    // Log urgency
    if (isUrgent) {
      console.log(`  🚨 URGENT EMAIL DETECTED!`);
    }
    
    // Store decision
    const decisionId = `decision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    await db.collection('agent_decisions').doc(decisionId).set({
      ...decision,
      email_id: email.id || 'unknown',
      sender: email.from || 'unknown',
      subject: email.subject || 'No Subject',
      timestamp: new Date().toISOString(),
      notified: false
    });

    // Notify user about important email
    console.log(`  🔔 SENDING DISCORD NOTIFICATION`);
    await notifyUserAboutEmail(decisionId, { ...decision, email });
    
    // Mark email as notified
    await docRef.update({ discord_notified: true });
    console.log(`  ✅ Notification complete`);
    
  } catch (error) {
    console.error('  ❌ Error in checkAndNotifyEmail:', error.message);
  }
}

async function checkForUnprocessedEmails() {
  try {
    console.log(`  📋 Checking for unprocessed emails...`);
    // Simple query - just get recent emails and filter in code
    const snapshot = await db.collection('emails')
      .orderBy('timestamp', 'desc')
      .limit(10)
      .get();

    if (snapshot.empty) {
      console.log(`  ℹ️ No emails found in database`);
      return;
    }

    console.log(`  📧 Found ${snapshot.size} recent emails to check`);
    
    for (const doc of snapshot.docs) {
      const email = { id: doc.id, ...doc.data() };
      
      console.log(`    - Checking: "${(email.subject || '').slice(0, 30)}..." (notified: ${email.discord_notified})`);
      
      // Skip if already notified
      if (email.discord_notified === true) continue;
      
      // Skip SENT emails - only notify about received emails
      const isSent = email.is_sent || (!email.from && email.to);
      if (isSent) {
        // Mark as notified but don't send notification
        await doc.ref.update({ discord_notified: true });
        console.log(`    ⏩ Skipped: sent email`);
        continue;
      }
      
      // Process through agent
      const decision = await processEmailWithAgent(email);
      
      // PRIORITY NOTIFICATION LOGIC:
      // 1. Always notify if urgent or time-sensitive
      // 2. Notify if needs reply or should be starred
      // 3. Notify if high confidence (>70%)
      const isUrgent = decision.is_urgent || decision.is_time_sensitive;
      const isImportant = decision.action === 'reply' || decision.action === 'star';
      const isHighConfidence = decision.confidence && decision.confidence > 0.7;
      
      const shouldNotify = isUrgent || isImportant || isHighConfidence;
      
      if (!shouldNotify) {
        // Mark as notified without sending Discord notification
        await doc.ref.update({ discord_notified: true });
        console.log(`  ⏩ Skipped notification: "${(email.subject || '').slice(0, 30)}..." (not important)`);
        continue;
      }
      
      // Log urgency
      if (isUrgent) {
        console.log(`  🚨 URGENT EMAIL DETECTED: "${(email.subject || '').slice(0, 30)}..."`);
      }
      
      // Store decision
      const decisionId = `decision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      await db.collection('agent_decisions').doc(decisionId).set({
        ...decision,
        email_id: email.id || 'unknown',
        sender: email.from || 'unknown',
        subject: email.subject || 'No Subject',
        timestamp: new Date().toISOString(),
        notified: false
      });

      // Notify user about important email
      console.log(`  🔔 Notifying: "${(email.subject || '').slice(0, 30)}..." (${decision.action})`);
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
  
  // Determine if this is a sent or received email
  const isSent = email.is_sent || (!email.from && email.to);
  const contactInfo = isSent 
    ? `To: ${email.to || 'Unknown'}` 
    : `From: ${email.from || 'Unknown'}`;

  // Store for feedback tracking with expiry timestamp
  pendingDecisions.set(decisionId, { 
    decision, 
    email,
    expiresAt: Date.now() + DECISION_EXPIRY_MS
  });

  // Color based on urgency and action
  let embedColor;
  if (decision.is_urgent || decision.is_time_sensitive) {
    embedColor = 0xFF0000;  // Bright red for urgent
  } else {
    const colors = {
      reply: 0xFF6B6B,    // Red - needs response
      star: 0xFFE66D,     // Yellow - important
      archive: 0x4ECDC4,  // Teal - can archive
      ignore: 0x95A5A6    // Gray - spam
    };
    embedColor = colors[action] || 0x7289DA;
  }

  // Build urgency indicator
  let urgencyEmoji = '';
  if (decision.is_urgent) urgencyEmoji = '🚨 URGENT';
  else if (decision.is_time_sensitive) urgencyEmoji = '⏰ TIME-SENSITIVE';
  
  const titlePrefix = urgencyEmoji ? `${urgencyEmoji} - ` : '';

  // Build email body preview (first 500 chars)
  const emailBody = email.body || email.snippet || 'No content';
  const bodyPreview = emailBody.length > 500 ? emailBody.slice(0, 500) + '...' : emailBody;
  
  const embed = new EmbedBuilder()
    .setColor(embedColor)
    .setTitle(`${titlePrefix}${isSent ? '📤' : '📧'} ${email.subject || 'New Email'}`)
    .addFields(
      { name: isSent ? 'To' : 'From', value: isSent ? (email.to || 'Unknown') : (email.from || 'Unknown'), inline: true },
      { name: 'Action', value: action.toUpperCase(), inline: true },
      { name: 'Confidence', value: `${Math.round(confidence * 100)}%`, inline: true },
      { name: 'Email Content', value: bodyPreview, inline: false }
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

async function generateDraftResponse(email, userMessage) {
  try {
    // Try Python agent first
    try {
      const response = await fetch('http://localhost:5001/generate-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          user_message: userMessage
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          console.log('  🐍 Using Python agent for draft');
          return result.draft;
        }
      }
    } catch (agentError) {
      console.log('  ⚠️ Python agent unavailable for drafting, using fallback');
    }
    
    // Fallback: Use Groq directly with sender style matching
    // Get SENDER's previous emails to learn THEIR style (how they write to you)
    const senderEmail = email.from;
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Query timeout')), 5000)
    );
    
    // Query emails FROM this sender (emails you received from them)
    const queryPromise = db.collection('emails')
      .orderBy('timestamp', 'desc')
      .limit(50)
      .get();
    
    let styleExamples = [];
    try {
      const allEmails = await Promise.race([queryPromise, timeoutPromise]);
      allEmails.forEach(doc => {
        const emailData = doc.data();
        // Only get emails FROM the sender (not sent TO them)
        if (emailData.from === senderEmail && !emailData.is_sent && emailData.body && emailData.body.length > 20) {
          styleExamples.push({
            subject: emailData.subject || '',
            body: emailData.body.slice(0, 400)
          });
        }
      });
    } catch (error) {
      console.log('⚠️ Could not fetch sender emails for style:', error.message);
      // Continue without style examples
    }

    let styleContext = '';
    if (styleExamples.length > 0) {
      styleContext = `\n\nSENDER'S WRITING STYLE (how ${senderEmail} writes):\n`;
      styleExamples.slice(0, 3).forEach((ex, i) => {
        styleContext += `\nExample ${i+1}:\nSubject: ${ex.subject}\nBody: ${ex.body}\n`;
      });
      styleContext += '\n---\nMatch this person\'s style: tone, formality, length, punctuation, emoji usage.';
    }

    const prompt = `You are responding to an email. Write in a style that MIRRORS how the sender writes.

CRITICAL INSTRUCTIONS:
1. The user wants to convey: "${userMessage}"
2. Write the response matching the SENDER'S style from their examples below
3. If they write casual → write casual. If formal → write formal
4. Match their typical length, tone, punctuation patterns
5. Mirror their greeting/closing style (or lack thereof)
${styleContext}

EMAIL YOU'RE RESPONDING TO:
From: ${email.from}
Subject: ${email.subject}
Body: ${(email.body || '').slice(0, 600)}

USER WANTS TO SAY: "${userMessage}"

Write a response that mirrors ${email.from}'s style. Make it feel natural like a reply in their conversational style.`;

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
  // Handle modal submissions
  if (interaction.isModalSubmit()) {
    if (interaction.customId.startsWith('draftmodal_')) {
      try {
        await interaction.deferReply();
        
        const decisionId = interaction.customId.replace('draftmodal_', '');
        const pending = pendingDecisions.get(decisionId);
        
        if (!pending || !pending.email) {
          await interaction.editReply('❌ Could not find the email. It may have expired.');
          return;
        }

        const userMessage = interaction.fields.getTextInputValue('responseText');
        const draft = await generateDraftResponse(pending.email, userMessage);
        
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
      } catch (error) {
        console.error('Modal submission error:', error);
        try {
          if (!interaction.replied && !interaction.deferred) {
            await interaction.reply({ content: '❌ Something went wrong. Please try again.', ephemeral: true });
          } else {
            await interaction.editReply({ content: '❌ Something went wrong. Please try again.', embeds: [], components: [] });
          }
        } catch (replyError) {
          console.error('Failed to send error message:', replyError);
        }
      }
    }
    return;
  }

  if (!interaction.isButton()) return;

  // Extract action and decisionId from button customId
  // Format can be: action_decisionId OR action_subaction_decisionId
  const customId = interaction.customId;
  let action, decisionId;
  
  // Handle multi-part actions (like should_reply, setaction_reply)
  if (customId.startsWith('should_reply_')) {
    action = 'should_reply';
    decisionId = customId.replace('should_reply_', '');
  } else if (customId.startsWith('setaction_')) {
    const parts = customId.split('_');
    action = `${parts[0]}_${parts[1]}`; // setaction_reply, setaction_star, etc
    decisionId = parts.slice(2).join('_');
  } else {
    // Simple format: action_decisionId
    const firstUnderscore = customId.indexOf('_');
    action = customId.substring(0, firstUnderscore);
    decisionId = customId.substring(firstUnderscore + 1);
  }

  const pending = pendingDecisions.get(decisionId);

  try {
    // ---- CONFIRM CORRECT ----
    if (interaction.customId.startsWith('confirm_')) {
      console.log(`✅ Confirming decision: ${decisionId}`);
      await recordFeedback(decisionId, 'action_correct');
      await interaction.reply({ content: '✅ Got it! I\'ll remember this for similar emails.', ephemeral: true });
    }

    // ---- DRAFT RESPONSE ----
    else if (interaction.customId.startsWith('draft_')) {
      if (!pending || !pending.email) {
        await interaction.reply({ content: '❌ Could not find the email. It may have expired.', ephemeral: true });
        return;
      }

      // Show modal to ask what user wants to say
      const modal = new ModalBuilder()
        .setCustomId(`draftmodal_${decisionId}`)
        .setTitle('What do you want to say?');

      const responseInput = new TextInputBuilder()
        .setCustomId('responseText')
        .setLabel('Your message (I\'ll match your style)')
        .setStyle(TextInputStyle.Paragraph)
        .setPlaceholder('e.g., "yeah I\'m coming, see you at 7"')
        .setRequired(true)
        .setMaxLength(1000);

      const row = new ActionRowBuilder().addComponents(responseInput);
      modal.addComponents(row);

      await interaction.showModal(modal);
      return;
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
      console.log(`📝 Should reply clicked for: ${decisionId}`);
      console.log(`  Checking pendingDecisions cache...`);
      console.log(`  Cache has ${pendingDecisions.size} decisions`);
      console.log(`  Decision exists: ${pendingDecisions.has(decisionId)}`);
      
      if (!pending || !pending.email) {
        console.log(`  ❌ ERROR: pending=${!!pending}, email=${pending?.email ? 'exists' : 'missing'}`);
        await interaction.reply({ content: '❌ Could not find the email. It may have expired.', ephemeral: true });
        return;
      }
      
      console.log(`  ✅ Found email, showing modal`);
      await recordFeedback(decisionId, 'action_wrong', 'reply');

      // Show modal to ask what user wants to say
      const modal = new ModalBuilder()
        .setCustomId(`draftmodal_${decisionId}`)
        .setTitle('What do you want to say?');

      const responseInput = new TextInputBuilder()
        .setCustomId('responseText')
        .setLabel('Your message')
        .setStyle(TextInputStyle.Paragraph)
        .setPlaceholder('e.g., "yeah I\'m coming, see you at 7"')
        .setRequired(true)
        .setMaxLength(1000);

      const actionRow = new ActionRowBuilder().addComponents(responseInput);
      modal.addComponents(actionRow);

      await interaction.showModal(modal);
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
// MESSAGE HANDLING (Chat with Memory)
// ============================================================

/**
 * Search emails in Firebase based on keywords
 */
async function searchEmails(query) {
  const queryLower = query.toLowerCase();
  const keywords = queryLower.split(/\s+/).filter(w => w.length > 2);
  const results = [];
  
  // Detect search intent: "from X" vs "to X" vs "sent to X" vs "recent"
  const fromMatch = queryLower.match(/(?:from|by)\s+(\w+)/);
  const toMatch = queryLower.match(/(?:to|sent to|sent)\s+(\w+)/);
  const isRecentQuery = /recent|latest|new|last/.test(queryLower);
  
  const searchFromPerson = fromMatch ? fromMatch[1] : null;  // Looking for emails RECEIVED from this person
  const searchToPerson = toMatch ? toMatch[1] : null;        // Looking for emails SENT to this person
  
  console.log(`[Search] Query: "${query}"`);
  console.log(`[Search] Looking for emails FROM: ${searchFromPerson || 'any'}, TO: ${searchToPerson || 'any'}, RECENT: ${isRecentQuery}`);
  
  try {
    const snapshot = await db.collection('emails')
      .orderBy('timestamp', 'desc')
      .limit(100)
      .get();
    
    snapshot.forEach(doc => {
      const email = { id: doc.id, ...doc.data() };
      const subject = (email.subject || '').toLowerCase();
      const from = (email.from || '').toLowerCase();
      const to = (email.to || '').toLowerCase();
      const body = (email.body || email.snippet || '').toLowerCase();
      const isSent = email.is_sent || (!email.from && email.to);
      
      let matchScore = 0;
      
      // If user explicitly asked for emails "from X", only match RECEIVED emails (not sent)
      if (searchFromPerson) {
        if (isSent) {
          // This is a SENT email - skip it when looking for "from X"
          return;
        }
        if (from.includes(searchFromPerson)) {
          matchScore += 10;  // Strong match on sender
        } else {
          return;  // Skip if sender doesn't match
        }
      }
      
      // If user explicitly asked for emails "to X" or "sent to X", only match SENT emails
      if (searchToPerson) {
        if (!isSent) {
          // This is a RECEIVED email - skip it when looking for "sent to X"
          return;
        }
        if (to.includes(searchToPerson)) {
          matchScore += 10;  // Strong match on recipient
        } else {
          return;  // Skip if recipient doesn't match
        }
      }
      
      // General keyword matching (for queries without explicit from/to)
      if (!searchFromPerson && !searchToPerson) {
        matchScore = keywords.reduce((score, keyword) => {
          if (subject.includes(keyword)) score += 3;
          if (from.includes(keyword)) score += 2;
          if (body.includes(keyword)) score += 1;
          return score;
        }, 0);
      } else {
        // Add bonus for subject/body matches
        keywords.forEach(keyword => {
          if (subject.includes(keyword)) matchScore += 2;
          if (body.includes(keyword)) matchScore += 1;
        });
      }
      
      if (matchScore > 0 || isRecentQuery) {
        results.push({ ...email, matchScore, isSent });
      }
    });
    
    // Sort by timestamp if asking for recent, otherwise by match score
    if (isRecentQuery) {
      results.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
      console.log(`[Search] Found ${results.length} recent emails (sorted by time)`);
    } else {
      results.sort((a, b) => b.matchScore - a.matchScore);
      console.log(`[Search] Found ${results.length} matching emails (sorted by relevance)`);
    }
    return results.slice(0, 5);
  } catch (error) {
    console.error('Email search error:', error);
    return [];
  }
}

/**
 * Get conversation history for a user
 */
function getConversationHistory(userId) {
  if (!conversationHistory.has(userId)) {
    conversationHistory.set(userId, []);
  }
  return conversationHistory.get(userId);
}

/**
 * Add message to conversation history
 */
function addToHistory(userId, role, content) {
  const history = getConversationHistory(userId);
  history.push({ role, content });
  
  // Trim if too long
  if (history.length > MAX_HISTORY_LENGTH) {
    history.splice(0, history.length - MAX_HISTORY_LENGTH);
  }
}

// ============================================================
// METRICS COMMANDS - Query agent learning stats
// ============================================================

async function getAgentMetrics() {
  try {
    const response = await fetch('http://localhost:5002/api/metrics');
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.log('Metrics dashboard unavailable');
  }
  return null;
}

async function formatMetricsEmbed(metrics) {
  if (!metrics) {
    return new EmbedBuilder()
      .setColor(0xff6b6b)
      .setTitle('📊 Metrics Dashboard Offline')
      .setDescription('Start the metrics dashboard with:\n```python agent/metrics_dashboard.py```')
      .setTimestamp();
  }

  const embed = new EmbedBuilder()
    .setColor(0x667eea)
    .setTitle('🧠 Agent Learning Metrics')
    .setDescription('Real-time self-learning statistics')
    .setTimestamp();

  // Learning proof
  if (metrics.learning_proof) {
    let learningText = '';
    if (metrics.learning_proof.confidence_improvement !== undefined) {
      const improvement = (metrics.learning_proof.confidence_improvement * 100).toFixed(1);
      const emoji = metrics.learning_proof.is_learning ? '📈' : '📊';
      learningText += `${emoji} Confidence: ${improvement > 0 ? '+' : ''}${improvement}%\n`;
    }
    if (metrics.learning_proof.total_feedback !== undefined) {
      learningText += `💬 Total Feedback: ${metrics.learning_proof.total_feedback}\n`;
    }
    if (learningText) {
      embed.addFields({ name: '🧠 Learning Proof', value: learningText, inline: false });
    }
  }

  // Decisions
  if (metrics.decisions && metrics.decisions.total_decisions) {
    let decisionsText = `📊 Total: ${metrics.decisions.total_decisions}\n`;
    if (metrics.decisions.recent_confidence) {
      const conf = (metrics.decisions.recent_confidence.avg * 100).toFixed(1);
      decisionsText += `⚡ Recent Confidence: ${conf}%\n`;
    }
    if (metrics.decisions.older_confidence) {
      const conf = (metrics.decisions.older_confidence.avg * 100).toFixed(1);
      decisionsText += `📉 Older Confidence: ${conf}%\n`;
    }
    embed.addFields({ name: '⚡ Decisions', value: decisionsText, inline: true });
  }

  // People graph
  if (metrics.people_graph && metrics.people_graph.total_people) {
    let peopleText = `👥 Total: ${metrics.people_graph.total_people}\n`;
    if (metrics.people_graph.importance_dist) {
      const dist = metrics.people_graph.importance_dist;
      peopleText += `🔴 High: ${dist.high || 0} | 🟡 Med: ${dist.medium || 0} | ⚪ Low: ${dist.low || 0}`;
    }
    embed.addFields({ name: '👥 People Graph', value: peopleText, inline: true });
  }

  // Patterns
  if (metrics.patterns && metrics.patterns.total_rules !== undefined) {
    let patternsText = `📚 Total Rules: ${metrics.patterns.total_rules}\n`;
    if (metrics.patterns.recent_rules && metrics.patterns.recent_rules.length > 0) {
      patternsText += '\n**Recent:**\n';
      metrics.patterns.recent_rules.slice(0, 3).forEach((rule, i) => {
        const conf = (rule.confidence * 100).toFixed(0);
        patternsText += `${i + 1}. ${rule.description} (${conf}%)\n`;
      });
    }
    embed.addFields({ name: '📊 Learned Patterns', value: patternsText, inline: false });
  }

  // Exploration
  if (metrics.exploration && metrics.exploration.total_hypotheses) {
    let exploreText = `🔬 Hypotheses: ${metrics.exploration.total_hypotheses}\n`;
    exploreText += `✅ Validated: ${metrics.exploration.validated || 0}\n`;
    exploreText += `❌ Rejected: ${metrics.exploration.rejected || 0}\n`;
    if (metrics.exploration.success_rate !== undefined) {
      const rate = (metrics.exploration.success_rate * 100).toFixed(1);
      exploreText += `📈 Success Rate: ${rate}%`;
    }
    embed.addFields({ name: '🔬 Exploration', value: exploreText, inline: true });
  }

  embed.setFooter({ text: 'View full dashboard: http://localhost:5002/dashboard' });

  return embed;
}

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (message.channel.id !== process.env.DISCORD_CHANNEL_ID) return;

  // Prevent duplicate processing of the same message
  if (processedMessages.has(message.id)) return;
  processedMessages.add(message.id);
  
  // Clean up old message IDs (keep last 100)
  if (processedMessages.size > 100) {
    const arr = Array.from(processedMessages);
    processedMessages.clear();
    arr.slice(-50).forEach(id => processedMessages.add(id));
  }

  const userId = message.author.id;
  const userMessage = message.content;
  
  // Show typing
  await message.channel.sendTyping();
  
  // Add user message to history
  addToHistory(userId, 'user', userMessage);

  try {
    // SPECIAL COMMAND: Show metrics
    if (userMessage.toLowerCase().includes('show metrics') || 
        userMessage.toLowerCase().includes('show stats') || 
        userMessage.toLowerCase().includes('agent metrics') ||
        userMessage.toLowerCase() === 'metrics') {
      console.log('📊 Fetching agent metrics...');
      const metrics = await getAgentMetrics();
      const embed = await formatMetricsEmbed(metrics);
      await message.reply({ embeds: [embed] });
      return;
    }
    
    // Check if user is asking about emails
    const emailKeywords = ['email', 'emails', 'inbox', 'message', 'externship', 'internship', 'job', 'interview', 'meeting', 'appointment', 'from', 'sent', 'received', 'canvas', 'professor', 'class', 'abraham', 'abe'];
    const isAskingAboutEmails = emailKeywords.some(kw => userMessage.toLowerCase().includes(kw));
    
    // Check if user wants to see a specific email from cached results
    const cachedResults = emailSearchCache.get(userId);
    const numMatch = userMessage.match(/^(\d+)$/); // Just a number like "1" or "2"
    
    // Handle direct number selection for cached emails
    if (numMatch && cachedResults && cachedResults.length > 0) {
      const idx = parseInt(numMatch[1]) - 1;
      if (idx >= 0 && idx < cachedResults.length) {
        const selectedEmail = cachedResults[idx];
        const isSent = selectedEmail.is_sent || (!selectedEmail.from && selectedEmail.to);
        let response = `📧 **Full Email Details:**\n\n`;
        response += `**Subject:** ${selectedEmail.subject || 'No Subject'}\n`;
        response += isSent 
          ? `**To:** ${selectedEmail.to || 'Unknown'}\n`
          : `**From:** ${selectedEmail.from || 'Unknown'}\n`;
        response += `**Date:** ${selectedEmail.date || selectedEmail.timestamp || 'Unknown'}\n\n`;
        response += `**Body:**\n\`\`\`\n${(selectedEmail.body || selectedEmail.snippet || 'No content available').slice(0, 1500)}\n\`\`\``;
        
        addToHistory(userId, 'assistant', response);
        await message.reply(response);
        return;
      }
    }
    
    // For email queries: Search DB first, then let LLM respond using ONLY that data
    let emailContext = '';
    let searchResults = [];
    
    if (isAskingAboutEmails) {
      searchResults = await searchEmails(userMessage);
      console.log(`🔍 Email search for "${userMessage.slice(0, 30)}..." found ${searchResults.length} results`);
      
      if (searchResults.length > 0) {
        emailSearchCache.set(userId, searchResults);
        
        emailContext = '\n\n=== REAL EMAILS FROM DATABASE (USE ONLY THESE) ===\n';
        searchResults.forEach((email, i) => {
          const isSent = email.is_sent || (!email.from && email.to);
          emailContext += `\n[Email ${i + 1}]\n`;
          emailContext += `  Subject: ${email.subject || 'No Subject'}\n`;
          emailContext += isSent 
            ? `  To: ${email.to || 'Unknown'} (SENT BY USER)\n`
            : `  From: ${email.from || 'Unknown'} (RECEIVED)\n`;
          emailContext += `  Body Preview: ${(email.body || email.snippet || '').slice(0, 200)}\n`;
        });
        emailContext += '\n=== END OF REAL EMAILS ===\n';
      } else {
        emailContext = '\n\n=== DATABASE SEARCH RESULT: NO EMAILS FOUND ===\nThe search returned 0 results. Tell the user honestly that you could not find any emails matching their query.\n';
      }
    }

    // Get conversation history for context
    const history = getConversationHistory(userId);
    
    // Build messages for LLM
    const systemPrompt = `You are Inscriptum, a helpful email assistant. You help users manage their inbox.

CRITICAL RULES YOU MUST FOLLOW:
1. You can ONLY mention emails that appear in the "REAL EMAILS FROM DATABASE" section below
2. If no emails are found, say "I couldn't find any emails matching that" - DO NOT invent any
3. NEVER make up email addresses, company names, or email content
4. When listing emails, use the EXACT subject, sender, and preview from the database
5. If user asks to see an email, tell them to reply with the number (1, 2, 3, etc.)
6. Keep responses conversational but accurate
7. You can summarize or explain emails, but NEVER add information that isn't in the data

${emailContext}`;

    const messages = [
      { role: 'system', content: systemPrompt },
      ...history.slice(-10)
    ];

    console.log(`💬 LLM query with ${searchResults.length} email results as context`);

    const completion = await groq.chat.completions.create({
      messages,
      model: 'llama-3.1-8b-instant',
      temperature: 0.3, // Lower = more factual
      max_tokens: 500,
    });

    const response = completion.choices[0]?.message?.content || "Sorry, I couldn't process that.";
    
    addToHistory(userId, 'assistant', response);
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

    // Enable automatic notifications for important/time-sensitive emails
    console.log('🔔 Email notifications ENABLED (will alert on important emails)');
    
    // Check for any existing important unprocessed emails on startup
    console.log('🔍 Checking for existing important emails...');
    await checkForUnprocessedEmails();
    
    // Start continuous Gmail scraping (every 5 SECONDS for testing)
    console.log('📥 Starting Gmail scraper (every 5 seconds)...');
    await scrapeNewEmails(); // Initial scrape
    setInterval(scrapeNewEmails, 5000); // Every 5 seconds for testing
    
    // Periodically check for unprocessed emails (every 2 minutes)
    setInterval(async () => {
      console.log('🔄 Periodic check for unprocessed emails...');
      await checkForUnprocessedEmails();
    }, 120000); // Every 2 minutes
    
    console.log('👥 People will be added as new emails arrive');
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
    pendingDrafts: pendingDrafts.size,
    lastScrape: new Date(lastScrapeTime).toISOString()
  });
});

app.listen(process.env.PORT || 3000, () => {
  console.log(`🌐 Server running on port ${process.env.PORT || 3000}`);
});

client.login(process.env.DISCORD_BOT_TOKEN);
