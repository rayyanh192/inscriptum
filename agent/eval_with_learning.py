"""
Evaluation WITH Learning Context - Tests agent after training
"""

import sys
sys.path.insert(0, '.')

import weave
import asyncio
import os
from dotenv import load_dotenv
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# Load env
load_dotenv('.env')
if not os.getenv('GROQ_API_KEY'):
    load_dotenv('agent/.env')

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
weave.init(project_name=os.getenv('WANDB_PROJECT', 'email-agent'))

# Direct LLM client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Test emails (same as before)
test_emails = [
    {
        "id": "test_1",
        "from": "boss@company.com",
        "subject": "Urgent: Need report by 5pm",
        "body": "Can you send me the Q4 report before end of day?",
        "expected_action": "respond",
        "expected_urgent": True
    },
    {
        "id": "test_2",
        "from": "newsletter@marketing.com",
        "subject": "Weekly Newsletter - Feb 2025",
        "body": "Check out this week's top stories and promotions!",
        "expected_action": "archive",
        "expected_urgent": False
    },
    {
        "id": "test_3",
        "from": "client@important.com",
        "subject": "Re: Project deadline concerns",
        "body": "I'm worried we won't meet the deadline. Can we discuss?",
        "expected_action": "respond",
        "expected_urgent": True
    },
    {
        "id": "test_4",
        "from": "spam@offers.com",
        "subject": "CONGRATULATIONS! You won $1000",
        "body": "Click here to claim your prize now!!!",
        "expected_action": "delete",
        "expected_urgent": False
    },
    {
        "id": "test_5",
        "from": "team@company.com",
        "subject": "FYI: Office closed tomorrow",
        "body": "Heads up - office will be closed for maintenance tomorrow.",
        "expected_action": "notify",
        "expected_urgent": False
    }
]

@weave.op()
def get_learned_patterns(sender: str) -> str:
    """Check if we have learned patterns for this sender domain."""
    domain = sender.split('@')[1] if '@' in sender else sender
    
    patterns = []
    for doc in db.collection('learned_patterns').where('sender_domain', '==', domain).limit(3).stream():
        data = doc.to_dict()
        patterns.append(f"- Learned: {data.get('preferred_action')} (confidence: {data.get('confidence', 0):.0%}) - {data.get('reasoning', '')}")
    
    if patterns:
        return "\n".join(patterns)
    return "No learned patterns for this sender."

@weave.op()
async def decide_with_learning(email: dict) -> dict:
    """Make decision using email content + learned patterns."""
    
    # Get learned patterns
    learned = get_learned_patterns(email['from'])
    
    prompt = f"""Analyze this email and decide the best action.

Email:
- From: {email['from']}
- Subject: {email['subject']}
- Body: {email['body']}

Learned Patterns:
{learned}

Available Actions:
- 'respond': Reply needed
- 'archive': Low priority, archive
- 'delete': Spam/unwanted
- 'notify': Just FYI
- 'star': Important, save for later
- 'ask': Uncertain, ask user

IMPORTANT: If there are learned patterns above, strongly prefer those actions.

Respond in JSON:
{{"action": "...", "confidence": 0.0-1.0, "reasoning": "why", "used_learning": true/false}}
"""
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    return {
        "action": result.get("action", "ask"),
        "confidence": result.get("confidence", 0.5),
        "reasoning": result.get("reasoning", ""),
        "used_learning": result.get("used_learning", False)
    }

@weave.op()
def evaluate_decision(expected: dict, actual: dict) -> dict:
    """Score the decision."""
    
    expected_action = expected["expected_action"]
    actual_action = actual["action"]
    
    # Map similar actions
    action_map = {
        "reply": "respond",
        "respond": "respond",
        "archive": "archive",
        "delete": "delete",
        "notify": "notify",
        "star": "star",
        "ask": "ask"
    }
    
    expected_norm = action_map.get(expected_action, expected_action)
    actual_norm = action_map.get(actual_action, actual_action)
    
    correct = expected_norm == actual_norm
    score = 1.0 if correct else 0.0
    
    return {
        "score": score,
        "correct": correct,
        "expected": expected_norm,
        "actual": actual_norm
    }

class LearnedEmailEvaluator(weave.Model):
    @weave.op()
    async def predict(self, email: dict) -> dict:
        return await decide_with_learning(email)

async def run_evaluation():
    """Run evaluation with learning context."""
    
    print("=" * 70)
    print("🧠 EVALUATION WITH LEARNING")
    print("=" * 70)
    
    evaluator = LearnedEmailEvaluator()
    
    total_score = 0
    results = []
    
    for i, email in enumerate(test_emails, 1):
        print(f"\n⏳ Processing {i}/5: {email['subject'][:50]}...")
        
        # Get decision (now uses learned patterns)
        decision = await evaluator.predict(email)
        
        # Evaluate
        eval_result = evaluate_decision(email, decision)
        
        total_score += eval_result["score"]
        results.append({
            "email": email["subject"],
            "expected": eval_result["expected"],
            "actual": eval_result["actual"],
            "correct": eval_result["correct"],
            "confidence": decision["confidence"],
            "used_learning": decision.get("used_learning", False)
        })
        
        status = "✅" if eval_result["correct"] else "❌"
        learning_badge = "🧠" if decision.get("used_learning") else "🤖"
        print(f"   {status} {learning_badge} Expected: {eval_result['expected']}, Got: {eval_result['actual']}")
        print(f"   Confidence: {decision['confidence']:.0%}")
        
        # Small delay
        await asyncio.sleep(2)
    
    # Final results
    accuracy = (total_score / len(test_emails)) * 100
    baseline = 80  # Previous baseline
    improvement = accuracy - baseline
    
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"Accuracy: {accuracy:.0f}% ({int(total_score)}/{len(test_emails)} correct)")
    print(f"Baseline: {baseline:.0f}%")
    
    if improvement > 0:
        print(f"🎉 IMPROVEMENT: +{improvement:.0f}% (from {baseline}% → {accuracy}%)")
    else:
        print(f"No improvement yet (still at {accuracy}%)")
    
    print("\nDetails:")
    for r in results:
        status = "✅" if r["correct"] else "❌"
        learning = "🧠 Learned" if r["used_learning"] else "🤖 Base LLM"
        print(f"  {status} {r['email'][:50]}")
        print(f"     Expected: {r['expected']}, Got: {r['actual']} ({r['confidence']:.0%}) - {learning}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
