import { google } from 'googleapis';
import { authorize } from './auth.js';
import admin from 'firebase-admin';
import { readFileSync } from 'fs';

// Initialize Firebase
const serviceAccount = JSON.parse(readFileSync('./firebase-service-account.json', 'utf8'));
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });
}
const db = admin.firestore();

async function scrapeSentEmails() {
  console.log("\n" + "=".repeat(70));
  console.log("📤 SCRAPING YOUR SENT EMAILS");
  console.log("=".repeat(70));

  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  try {
    // Get user's sent emails
    console.log("\n🔑 Fetching sent emails from Gmail...");
    const res = await gmail.users.messages.list({
      userId: 'me',
      q: 'in:sent',  // Only sent emails
      maxResults: 50  // Last 50 sent emails
    });

    const messages = res.data.messages || [];
    console.log(`   Found ${messages.length} sent emails`);

    const sentEmails = [];
    const recipients = {};

    for (const message of messages) {
      const email = await gmail.users.messages.get({
        userId: 'me',
        id: message.id,
        format: 'full'
      });

      const headers = email.data.payload.headers;
      const subject = headers.find(h => h.name === 'Subject')?.value || 'No Subject';
      const to = headers.find(h => h.name === 'To')?.value || 'Unknown';
      const date = headers.find(h => h.name === 'Date')?.value || '';

      // Get email body
      let body = '';
      if (email.data.payload.body.data) {
        body = Buffer.from(email.data.payload.body.data, 'base64').toString();
      } else if (email.data.payload.parts) {
        const textPart = email.data.payload.parts.find(part => part.mimeType === 'text/plain');
        if (textPart && textPart.body.data) {
          body = Buffer.from(textPart.body.data, 'base64').toString();
        }
      }

      sentEmails.push({
        id: message.id,
        to: to,
        subject: subject,
        body: body.substring(0, 2000),  // Limit size
        date: date,
        internalDate: email.data.internalDate
      });

      // Track recipients
      let recipientEmail = to;
      if (to.includes('<') && to.includes('>')) {
        recipientEmail = to.split('<')[1].split('>')[0];
      }
      recipients[recipientEmail] = (recipients[recipientEmail] || 0) + 1;
    }

    console.log(`\n✅ Fetched ${sentEmails.length} sent emails`);

    // Show top recipients
    console.log(`\n👥 Top recipients:`);
    const sortedRecipients = Object.entries(recipients)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    for (const [recipient, count] of sortedRecipients) {
      console.log(`   ${recipient}: ${count} emails`);
    }

    // Store in Firebase
    console.log(`\n💾 Storing sent emails in Firebase...`);
    const batch = db.batch();
    let stored = 0;

    for (const email of sentEmails) {
      const docRef = db.collection('emails').doc(`sent_${email.id}`);
      batch.set(docRef, {
        id: `sent_${email.id}`,
        to: email.to,
        subject: email.subject,
        body: email.body,
        timestamp: email.date,
        is_sent: true,  // Mark as sent email
        has_reply: false,
        scraped_at: admin.firestore.FieldValue.serverTimestamp()
      });
      stored++;
    }

    await batch.commit();
    console.log(`✅ Stored ${stored} sent emails in emails/ collection`);

    console.log(`\n🎯 READY TO ANALYZE COMMUNICATION STYLE!`);
    console.log(`   These emails show HOW you write to different people`);
    console.log(`   Run: python analyze_style_from_sent.py`);

  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

scrapeSentEmails();
