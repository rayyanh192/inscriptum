"""
Scrape SENT emails from Gmail to learn communication style.
This fetches your actual sent emails to see how you write to different people.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import subprocess
import json

if not firebase_admin._apps:
    cred = credentials.Certificate('../convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

print("\n" + "="*70)
print("📤 SCRAPING YOUR SENT EMAILS")
print("="*70)

# Use Node.js to call Gmail API (existing auth is set up in convo/)
# We'll create a quick Node script
node_script = """
import { google } from 'googleapis';
import { authorize } from './auth.js';

async function fetchSentEmails() {
  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  try {
    // Get user's sent emails
    const res = await gmail.users.messages.list({
      userId: 'me',
      q: 'in:sent',  // Only sent emails
      maxResults: 50  // Last 50 sent emails
    });

    const messages = res.data.messages || [];
    console.error(`Found ${messages.length} sent emails`);

    const sentEmails = [];
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
    }

    console.log(JSON.stringify(sentEmails, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

fetchSentEmails();
"""

# Write temp Node script
import os
temp_script = '/tmp/fetch_sent_emails.mjs'
with open(temp_script, 'w') as f:
    f.write(node_script)

print("\n🔑 Using existing Gmail auth to fetch sent emails...")

# Run Node script
result = subprocess.run(
    ['node', temp_script],
    cwd='/Users/edrickchang/Desktop/inscriptum/convo',
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"❌ Error fetching sent emails: {result.stderr}")
    exit(1)

# Parse JSON output
try:
    sent_emails = json.loads(result.stdout)
except json.JSONDecodeError:
    print("❌ Failed to parse sent emails")
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    exit(1)

print(f"\n✅ Fetched {len(sent_emails)} sent emails")

# Analyze recipients
recipients = {}
for email in sent_emails:
    to = email['to']
    # Extract email from "Name <email@domain.com>" format
    if '<' in to and '>' in to:
        to = to.split('<')[1].split('>')[0]
    recipients[to] = recipients.get(to, 0) + 1

print(f"\n👥 Top recipients:")
for recipient, count in sorted(recipients.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"   {recipient}: {count} emails")

# Store in Firebase with sent=True flag
print(f"\n💾 Storing sent emails in Firebase...")
for email in sent_emails:
    doc_ref = db.collection('emails').document(f"sent_{email['id']}")
    doc_ref.set({
        'id': f"sent_{email['id']}",
        'to': email['to'],
        'subject': email['subject'],
        'body': email['body'],
        'timestamp': email['date'],
        'is_sent': True,  # Mark as sent email
        'has_reply': False,  # Not applicable for sent
        'scraped_at': firestore.SERVER_TIMESTAMP
    })

print(f"✅ Stored {len(sent_emails)} sent emails")
print(f"   Collection: emails/ (with is_sent=True)")

print(f"\n🎯 READY TO ANALYZE COMMUNICATION STYLE!")
print(f"   These emails show HOW you write to different people")
