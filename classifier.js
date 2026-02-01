import Groq from 'groq-sdk';
import dotenv from 'dotenv';

dotenv.config();

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

const CATEGORIES = [
  'marketing', 'personal', 'work', 'receipts', 'newsletters',
  'spam', 'social', 'finance', 'travel', 'shopping', 'other'
];

export async function classifyEmail(subject, body, from) {
    try {
      const response = await groq.chat.completions.create({
        model: "llama-3.3-70b-versatile",
        messages: [{
          role: "system",
          content: `You are an email classifier. Classify emails into EXACTLY ONE category:
  - marketing: promotional emails, sales, advertisements
  - personal: emails from friends/family, personal conversations
  - work: job-related, professional emails, work projects
  - receipts: purchase confirmations, invoices, payment receipts
  - newsletters: subscriptions, digests, regular updates
  - spam: unwanted bulk emails, suspicious content
  - social: social media notifications, friend requests
  - finance: banking, investments, credit cards, financial statements
  - travel: bookings, tickets, travel confirmations
  - shopping: order updates, shipping notifications
  - other: anything that doesn't fit above
  
  Respond with ONLY the category name.`
        }, {
          role: "user",
          content: `From: ${from || 'Unknown'}
  Subject: ${subject || 'No subject'}
  Body: ${body?.slice(0, 800) || 'No body'}`
        }],
        temperature: 0,
        max_tokens: 15
      });
      
      const category = response.choices[0].message.content.trim().toLowerCase();
      
      if (CATEGORIES.includes(category)) {
        return category;
      }
      
      console.log(`⚠️  Unknown category "${category}", defaulting to "other"`);
      return 'other';
    } catch (error) {
      console.error('❌ Classification error:', error.message);
      return 'other';
    }
  }