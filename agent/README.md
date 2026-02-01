# Self-Learning Email Agent

An AI-powered email assistant that learns from your Gmail behavior patterns to intelligently manage your inbox.

## Features

### 🧠 Self-Learning
- Learns what emails are important to you from starred, archived, and deleted patterns
- Adapts to your communication style by analyzing your replies
- Improves predictions based on your feedback

### 👥 People Graphing
- Maps relationships from email history
- Categorizes contacts (work, personal, marketing, etc.)
- Tracks importance scores per sender
- Clusters relationships for better context

### 📊 Importance Prediction
- Multi-signal importance scoring:
  - Person importance (from relationship history)
  - Gmail signals (starred, important, deleted)
  - Learned patterns (domain associations)
  - Content urgency (deadlines, action items)
  - Recency factor

### ✍️ Response Generation
- Learns your writing style (tone, formality, phrases)
- Generates contextual responses matching your style
- Quick reply suggestions
- Style adaptation per recipient

### 📈 Weave Tracing
- Full observability with W&B Weave
- Traces every decision for debugging
- Feedback loops for continuous improvement

## Architecture

```
agent/
├── __init__.py          # Weave + Firebase initialization
├── agent.py             # Main orchestrator
├── bootstrap.py         # Cold-start learning
├── people_graph.py      # Relationship mapping
├── style_learning.py    # Communication style analysis
├── importance.py        # Importance prediction
├── response_generator.py # Reply generation
├── decisions.py         # Action selection
├── execution.py         # Firebase operations
├── feedback.py          # Learning loops
└── test_full_agent.py   # Test suite
```

## Setup

### 1. Install Dependencies

```bash
cd agent
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` file:

```env
WANDB_API_KEY=your_wandb_key
GROQ_API_KEY=your_groq_key
```

### 3. Firebase Service Account

Place `firebase-service-account.json` in the `agent/` folder.

### 4. Run the Gmail Scraper (convo/)

First, sync your Gmail data:

```bash
cd convo
npm install
node data.js
```

This populates Firebase `emails/` collection with behavior metadata.

## Usage

### Initialize Agent (Cold Start)

```python
import asyncio
import weave
weave.init('email-agent')

from agent import initialize_agent

async def main():
    result = await initialize_agent()
    print(result)

asyncio.run(main())
```

### Process Inbox

```python
from agent import process_inbox

async def main():
    result = await process_inbox(limit=10)
    print(f"Processed {result['total_processed']} emails")

asyncio.run(main())
```

### Process Single Email

```python
from agent import process_email

email = {
    "id": "email_123",
    "from": "sender@example.com",
    "subject": "Important meeting",
    "snippet": "Let's meet tomorrow...",
    "is_read": False,
    "is_starred": False,
    # ... other fields
}

result = await process_email(email)
print(result['decision'])
```

### Get Agent Status

```python
from agent import get_agent_status

status = await get_agent_status()
print(f"People profiles: {status['statistics']['people_profiles']}")
print(f"Decisions made: {status['statistics']['decisions_made']}")
```

## Firebase Collections

| Collection | Purpose |
|------------|---------|
| `emails/` | Raw emails from Gmail scraper |
| `people/` | Person profiles with relationship data |
| `agent_decisions/` | Decisions for Discord bot |
| `generated_responses/` | Generated reply drafts |
| `training_feedback/` | Feedback for learning |
| `learned_patterns/` | Importance and style patterns |
| `relationship_clusters/` | Grouped relationships |

## Testing

```bash
cd agent
python test_full_agent.py
```

## W&B Weave Dashboard

View traces at: https://wandb.ai/YOUR_ENTITY/email-agent/weave

All operations are decorated with `@weave.op()` for full observability.

## Learning Loop

1. **Bootstrap**: Initial learning from Gmail history
2. **Process**: Analyze emails using learned models
3. **Decide**: Make action recommendations
4. **Feedback**: Record user corrections
5. **Improve**: Update models from feedback

## Actions

| Action | When Used |
|--------|-----------|
| `respond` | High importance, requires reply |
| `star` | Important but not urgent |
| `archive` | Low priority, already handled |
| `delete` | Spam, unwanted |
| `ask` | Uncertain, needs user input |
| `notify` | FYI only |

## Discord Integration

The Discord bot reads from `agent_decisions/` collection:

```javascript
// In Discord bot
const decisions = await db.collection('agent_decisions')
  .where('processed', '==', false)
  .get();

// Display to user, then mark as processed
await db.collection('agent_decisions')
  .doc(decisionId)
  .update({ processed: true });
```

## Contributing

1. All new functions should use `@weave.op()` decorator
2. Use `.get()` for all dictionary field access
3. Handle errors gracefully with fallbacks
4. Add tests for new functionality
