import admin from 'firebase-admin';
import { fetchEmails } from './scraper.js';
import { classifyEmail } from './classifier.js';
import dotenv from 'dotenv';
import fs from 'fs';

dotenv.config();

// Initialize Firebase
const serviceAccount = JSON.parse(fs.readFileSync('./firebase-service-account.json'));
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

// Function to extract all URLs from text
function extractLinks(text) {
  if (!text) return [];
  
  // Regex to match URLs
  const urlRegex = /(https?:\/\/[^\s<>"{}|\\^`\[\]]+)/gi;
  const matches = text.match(urlRegex);
  
  if (!matches) return [];
  
  // Remove duplicates and clean up
  return [...new Set(matches)].map(url => {
    // Remove trailing punctuation
    return url.replace(/[.,;!?)]$/, '');
  });
}

async function processEmails() {
  console.log('🚀 Starting email processing...');
  
  // Fetch emails
  const emails = await fetchEmails(50);
  console.log(`📊 Processing ${emails.length} emails...`);
  
  for (const email of emails) {
    // Check if already processed
    const docRef = db.collection('emails').doc(email.id);
    const doc = await docRef.get();
    
    if (doc.exists) {
      console.log(`⏭️  Skipping ${email.id} (already processed)`);
      continue;
    }
    
    // Get full email data
    const fullEmail = email.message;
    const text = fullEmail.snippet || '';
    const links = extractLinks(text);
    
    // Classify email
    const category = await classifyEmail(fullEmail.subject, text);
    
    // Store in Firestore with behavior metadata
    await docRef.set({
      from: fullEmail.from,
      subject: fullEmail.subject,
      snippet: fullEmail.snippet,
      timestamp: fullEmail.date,
      category: category,
      links: links,
      // Behavior metadata from Gmail
      is_read: email.is_read,
      is_archived: email.is_archived,
      is_deleted: email.is_deleted,
      is_starred: email.is_starred,
      is_important: email.is_important,
      labels: email.labels,
      thread_id: email.thread_id,
      internal_date: email.internal_date,
      days_unread: email.days_unread,
      has_reply: email.has_reply,
      last_synced: new Date().toISOString()
    });
    
    console.log(`✅ Stored ${email.id}`);
    
    // Rate limit: wait 2 seconds between classifications
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('✨ Done!');
  process.exit(0);
}

// Run once and exit
processEmails().catch(console.error);
