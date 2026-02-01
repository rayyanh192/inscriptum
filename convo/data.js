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
  const emails = await fetchEmails(10); // Adjust number as needed
  
  console.log(`📊 Processing ${emails.length} emails...`);
  
  for (const email of emails) {
    // Check if already processed
    const docRef = db.collection('emails').doc(email.id);
    const doc = await docRef.get();
    
    if (doc.exists) {
      console.log(`⏭️  Skipping ${email.id} (already processed)`);
      continue;
    }
    
    // Extract links from subject and body
    const links = extractLinks(email.subject + ' ' + email.body);
    
    
    // Classify
    console.log(`🔍 Classifying: ${email.subject}`);
    const category = await classifyEmail(email.subject, email.body, email.from);
    console.log(`   → Category: ${category}`);
    console.log(`   → Found ${links.length} link(s)`);
    
    // Store in Firebase
    await docRef.set({
      ...email,
      category,
      links: links,
      linkCount: links.length,
      processedAt: admin.firestore.FieldValue.serverTimestamp()
    });
    
    console.log(`✅ Stored ${email.id}`);
    
    // Rate limit: wait 2 seconds between classifications
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('✨ Done!');
}

async function runContinuously(intervalSeconds = 60) {
  console.log(`🔄 Running every ${intervalSeconds} seconds...`);
  
  while (true) {
    await processEmails();
    console.log(`⏰ Waiting ${intervalSeconds} seconds before next run...`);
    await new Promise(resolve => setTimeout(resolve, intervalSeconds * 1000));
  }
}

runContinuously(5).catch(console.error);