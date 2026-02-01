import { google } from 'googleapis';
import { authorize } from './auth.js';

export async function fetchEmails(maxResults = 100) {
  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  try {
    // Get list of message IDs
    const res = await gmail.users.messages.list({
      userId: 'me',
      maxResults: maxResults,
    });

    const messages = res.data.messages || [];
    console.log(`📧 Found ${messages.length} emails`);

    // Fetch full details for each email
    const emails = [];
    for (const message of messages) {
      const email = await gmail.users.messages.get({
        userId: 'me',
        id: message.id,
      });

      const headers = email.data.payload.headers;
      const subject = headers.find(h => h.name === 'Subject')?.value || 'No Subject';
      const from = headers.find(h => h.name === 'From')?.value || 'Unknown';
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

      emails.push({
        id: message.id,
        subject,
        from,
        date,
        body: body.slice(0, 1000), // Limit body length
        timestamp: new Date(date).getTime()
      });
    }

    return emails;
  } catch (error) {
    console.error('❌ Error fetching emails:', error.message);
    return [];
  }
}