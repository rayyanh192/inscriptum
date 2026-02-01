/**
 * Email Sender - Send emails via Gmail API
 */

import { google } from 'googleapis';
import { authorize } from './auth.js';

/**
 * Send an email via Gmail API
 * @param {string} to - Recipient email
 * @param {string} subject - Email subject
 * @param {string} body - Email body (plain text)
 * @param {string} threadId - Optional thread ID to reply to
 */
export async function sendEmail(to, subject, body, threadId = null) {
  const auth = await authorize();
  const gmail = google.gmail({ version: 'v1', auth });

  // Get user's email for From header
  const profile = await gmail.users.getProfile({ userId: 'me' });
  const fromEmail = profile.data.emailAddress;

  // Create email in RFC 2822 format
  const emailLines = [
    `From: ${fromEmail}`,
    `To: ${to}`,
    `Subject: ${subject}`,
    'Content-Type: text/plain; charset=utf-8',
    '',
    body
  ];

  const email = emailLines.join('\r\n');
  const encodedEmail = Buffer.from(email).toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  const params = {
    userId: 'me',
    requestBody: {
      raw: encodedEmail
    }
  };

  // If replying to a thread, include threadId
  if (threadId) {
    params.requestBody.threadId = threadId;
  }

  try {
    const result = await gmail.users.messages.send(params);
    console.log(`✅ Email sent: ${result.data.id}`);
    return {
      success: true,
      messageId: result.data.id,
      threadId: result.data.threadId
    };
  } catch (error) {
    console.error('❌ Failed to send email:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Create a reply to an email
 */
export async function replyToEmail(originalEmail, replyBody) {
  const to = originalEmail.from;
  const subject = originalEmail.subject.startsWith('Re:') 
    ? originalEmail.subject 
    : `Re: ${originalEmail.subject}`;
  
  return sendEmail(to, subject, replyBody, originalEmail.thread_id);
}
