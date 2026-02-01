import { google } from 'googleapis';
import { authorize } from './auth.js';

export async function fetchEmails(maxResults = 100) {
  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  try {
    // Get user's email address for has_reply detection
    const profile = await gmail.users.getProfile({ userId: 'me' });
    const userEmail = profile.data.emailAddress;

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
        format: 'full' // Get complete metadata including labels
      });

      const headers = email.data.payload.headers;
      const subject = headers.find(h => h.name === 'Subject')?.value || 'No Subject';
      
      // Extract email addresses from headers (Gmail returns "Name <email@domain.com>" format)
      const extractEmail = (headerValue) => {
        if (!headerValue) return '';
        const match = headerValue.match(/<([^>]+)>/);  // Extract email from angle brackets
        if (match) return match[1];  // Found email in brackets
        // If no brackets, check if it's already just an email
        if (headerValue.includes('@')) return headerValue.trim();
        return headerValue.trim();  // Return as-is if no @ symbol
      };
      
      const fromHeader = headers.find(h => h.name === 'From')?.value || 'Unknown';
      const toHeader = headers.find(h => h.name === 'To')?.value || '';
      const from = extractEmail(fromHeader);
      const to = extractEmail(toHeader);
      const date = headers.find(h => h.name === 'Date')?.value || '';
      
      // Extract label-based behavior signals (must be before is_sent check)
      const labelIds = email.data.labelIds || [];
      
      // Detect if this is a SENT email (from the user)
      const is_sent = labelIds.includes('SENT') || from.includes(userEmail);

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

      const is_read = !labelIds.includes('UNREAD');
      const is_starred = labelIds.includes('STARRED');
      const is_deleted = labelIds.includes('TRASH');
      const is_important = labelIds.includes('IMPORTANT');
      const is_archived = !labelIds.includes('INBOX') && !labelIds.includes('TRASH');

      // Get internal date (when Gmail received the email)
      const internal_date = parseInt(email.data.internalDate);
      
      // Calculate days_unread if email is unread
      let days_unread = null;
      if (!is_read) {
        const now = Date.now();
        days_unread = (now - internal_date) / (1000 * 60 * 60 * 24); // Convert ms to days
      }

      // Check if user has replied in this thread
      let has_reply = false;
      if (email.data.threadId) {
        try {
          const thread = await gmail.users.threads.get({
            userId: 'me',
            id: email.data.threadId
          });
          
          // Check if any message in thread is from user
          has_reply = thread.data.messages.some(msg => {
            const msgFrom = msg.payload.headers.find(h => h.name === 'From')?.value || '';
            return msgFrom.includes(userEmail);
          });
        } catch (error) {
          console.error(`Error checking thread ${email.data.threadId}:`, error.message);
        }
      }

      emails.push({
        id: message.id,
        subject,
        from,
        to,
        date,
        body: body.slice(0, 1000), // Limit body length
        timestamp: new Date(date).getTime(),
        
        // New behavior signals for training
        is_read,
        is_starred,
        is_deleted,
        is_important,
        is_archived,
        is_sent,
        labels: labelIds,
        thread_id: email.data.threadId || null,
        internal_date,
        days_unread,
        has_reply,
        last_synced: Date.now()
      });
    }

    return emails;
  } catch (error) {
    console.error('❌ Error fetching emails:', error.message);
    return [];
  }
}