# Email Agent - Usage Guide

## Setup Complete ✅

All files are ready and the agent is working!

## Files Created

- `__init__.py` - Weave initialization
- `agent.py` - Main entry point with `handle_email()`
- `decisions.py` - LLM-powered intent analysis and decision making
- `execution.py` - Firebase operations for storing decisions
- `test_agent.py` - Test script
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (already configured)
- `.env.example` - Template for environment variables

## How to Run

### Test the Agent
```bash
cd agent
../.venv/bin/python test_agent.py
```

### Use in Your Code
```python
from agent import handle_email

# Process an email
result = await handle_email(
    email_id='email_123',
    email_data={
        'from': 'sender@example.com',
        'subject': 'Email subject',
        'body': 'Email body text...',
        'links': ['https://example.com'],
        'category': 'newsletter'
    }
)

print(f"Action: {result['action']}")
print(f"Confidence: {result['confidence']}")
```

## Decision Types

- **`auto`** - High confidence (>0.8), safe to execute automatically
- **`ask`** - Medium confidence (0.5-0.8) or risky, ask user first  
- **`notify`** - Low confidence (<0.5) or informational, just notify

## Firebase Collection

Decisions are stored in `agent_decisions` collection with:
- Email details (from, subject, category)
- Intent analysis (intent, confidence, entities)
- Decision (action, reason, risk_level)
- Metadata (timestamp, processed flag)

## Weave Tracing

Each email creates one trace with child operations:
1. `handle_email` - Main entry point
2. `analyze_email_intent` - LLM intent analysis
3. `decide_action` - Decision making
4. `store_decision` - Firebase storage

To view traces, log in to W&B: https://wandb.ai/

## Next Steps

Integrate with Discord bot to:
1. Poll `agent_decisions` collection for new decisions
2. Display decisions to users in Discord
3. Collect user feedback and update Firebase
