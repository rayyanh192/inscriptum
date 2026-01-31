require('dotenv').config();
const express = require('express');
const { Client, GatewayIntentBits, Partials } = require('discord.js');
const Groq = require('groq-sdk');

const app = express();
app.use(express.json());

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

// Conversation history
const conversationHistory = [];

// System prompt - keep it simple for now, will add database context later
const SYSTEM_PROMPT = `You are a helpful personal assistant. Have natural, friendly conversations with the user. Keep responses concise.`;

let botReady = false;
let notificationChannel = null;

client.once('ready', async () => {
  console.log(`Discord bot logged in as ${client.user.tag}`);
  botReady = true;

  notificationChannel = client.channels.cache.get(process.env.DISCORD_CHANNEL_ID);
  if (notificationChannel) {
    console.log(`Notification channel: #${notificationChannel.name}`);

    // Send greeting
    await notificationChannel.send("Hey! I'm online and ready to chat. What's up?");
  } else {
    console.error('Could not find notification channel! Check DISCORD_CHANNEL_ID');
  }
});

// Chat with Groq
async function chat(userMessage) {
  conversationHistory.push({
    role: 'user',
    content: userMessage,
  });

  try {
    const completion = await groq.chat.completions.create({
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        ...conversationHistory.slice(-20), // Keep last 20 messages for context
      ],
      model: 'llama-3.3-70b-versatile',
      temperature: 0.7,
      max_tokens: 500,
    });

    const response = completion.choices[0]?.message?.content || "Sorry, I couldn't process that.";

    conversationHistory.push({
      role: 'assistant',
      content: response,
    });

    return response;
  } catch (error) {
    console.error('Groq API error:', error);
    return "Sorry, I'm having trouble thinking right now. Try again?";
  }
}

// Listen for messages
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (message.channel.id !== process.env.DISCORD_CHANNEL_ID) return;

  console.log(`${message.author.username}: ${message.content}`);

  // Show typing indicator
  await message.channel.sendTyping();

  // Get AI response
  const response = await chat(message.content);

  await message.reply(response);
});

// Health check
app.get('/', (req, res) => {
  res.json({
    status: 'running',
    botReady,
    channel: notificationChannel?.name || 'not connected',
  });
});

app.listen(process.env.PORT, () => {
  console.log(`Server running on port ${process.env.PORT}`);
});

client.login(process.env.DISCORD_BOT_TOKEN);
