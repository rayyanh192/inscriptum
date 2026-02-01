"""
Exploration Engine - Makes agent TRY NEW THINGS to learn
NOT pattern matching. ACTIVE EXPERIMENTATION.
"""

import weave
from groq import Groq
import os
import random
import json
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def should_explore(email_data: Dict, current_prediction: Dict, db) -> tuple[bool, float]:
    """
    Decide if agent should EXPLORE (try something new) or EXPLOIT (use known strategy).
    
    This is how the agent LEARNS - by trying alternatives.
    """
    confidence = current_prediction.get('confidence', 0.5)
    
    # Get recent decision history for similar emails
    decision_history = await get_similar_decisions(email_data, db)
    
    # Get overall performance
    performance = await get_recent_performance(db, days=7)
    
    # EXPLORATION TRIGGER 1: Low confidence - need more data
    if confidence < 0.6:
        exploration_rate = 0.4
        reason = "low_confidence"
    
    # EXPLORATION TRIGGER 2: Limited data for this context
    elif len(decision_history) < 10:
        exploration_rate = 0.3
        reason = "limited_data"
    
    # EXPLORATION TRIGGER 3: Performance has plateaued
    elif is_performance_plateaued(performance):
        exploration_rate = 0.5
        reason = "performance_plateau"
    
    # EXPLORATION TRIGGER 4: This is a new relationship type we haven't seen much
    elif is_novel_context(email_data, db):
        exploration_rate = 0.4
        reason = "novel_context"
    
    else:
        exploration_rate = 0.1  # Always explore a little
        reason = "baseline_exploration"
    
    explore = random.random() < exploration_rate
    
    return explore, exploration_rate


@weave.op()
async def generate_alternative_strategy(
    email_data: Dict,
    current_prediction: Dict,
    person_context: Dict,
    db
) -> Dict[str, Any]:
    """
    THE AGENT INVENTS NEW STRATEGIES HERE.
    
    This is CREATION, not retrieval.
    """
    
    # Build context for LLM to invent alternative
    prompt = f"""You are a meta-learning agent that invents new email handling strategies.

Current email:
- From: {email_data.get('from')}
- Subject: {email_data.get('subject', '')}
- Time: {email_data.get('timestamp', '')}
- Relationship: {person_context.get('relationship', {}).get('type', 'unknown')}
- Cluster patterns: {person_context.get('cluster_context', {}).get('patterns', 'unknown')}

Current strategy would be: {current_prediction.get('action')} (confidence: {current_prediction.get('confidence', 0):.2f})

Invent an ALTERNATIVE strategy to test. Consider hypotheses like:
- "What if time-of-day matters for this relationship type?"
- "What if subject keywords indicate urgency differently than assumed?"
- "What if this sender should be treated differently based on past behavior?"
- "What patterns might we be missing?"

Propose an alternative action and a testable hypothesis.

Return JSON:
{{
    "alternative_action": "reply/star/archive/ignore",
    "hypothesis": "Clear statement of what we're testing",
    "expected_outcome": "What should happen if hypothesis is correct",
    "success_criteria": "How to measure if this worked"
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # Higher temp for creativity
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        alternative = json.loads(response.choices[0].message.content)
        
        # Store hypothesis for later validation
        hypothesis_id = await store_hypothesis(
            hypothesis=alternative['hypothesis'],
            email_id=email_data.get('id'),
            alternative_action=alternative['alternative_action'],
            expected_outcome=alternative['expected_outcome'],
            email_context=email_data,
            db=db
        )
        
        return {
            'action': alternative['alternative_action'],
            'is_exploration': True,
            'hypothesis': alternative['hypothesis'],
            'hypothesis_id': hypothesis_id,
            'expected_outcome': alternative['expected_outcome'],
            'success_criteria': alternative['success_criteria'],
            'original_prediction': current_prediction,
            'confidence': 0.5  # Exploratory decisions have moderate confidence
        }
        
    except Exception as e:
        print(f"⚠️  Error generating alternative: {e}")
        return current_prediction


async def get_similar_decisions(email_data: Dict, db) -> List[Dict]:
    """Get recent decisions for similar emails."""
    relationship_type = email_data.get('relationship_type', 'unknown')
    
    decisions = []
    docs = db.collection('agent_decisions')\
        .where('relationship_type', '==', relationship_type)\
        .limit(20)\
        .stream()
    
    for doc in docs:
        decisions.append(doc.to_dict())
    
    return decisions


async def get_recent_performance(db, days=7) -> List[Dict]:
    """Get performance metrics over time."""
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    decisions = []
    docs = db.collection('agent_decisions')\
        .where('timestamp', '>=', cutoff)\
        .stream()
    
    for doc in docs:
        data = doc.to_dict()
        if 'feedback' in data:
            decisions.append({
                'accuracy': 1.0 if data['feedback'].get('correct') else 0.0,
                'confidence': data.get('decision', {}).get('confidence', 0.5)
            })
    
    return decisions


def is_performance_plateaued(performance: List[Dict]) -> bool:
    """Detect if performance has stopped improving."""
    if len(performance) < 20:
        return False
    
    recent_10 = performance[-10:]
    previous_10 = performance[-20:-10]
    
    if not recent_10 or not previous_10:
        return False
    
    avg_recent = sum(d['accuracy'] for d in recent_10) / len(recent_10)
    avg_previous = sum(d['accuracy'] for d in previous_10) / len(previous_10)
    
    improvement = avg_recent - avg_previous
    return improvement < 0.02  # Less than 2% improvement


async def is_novel_context(email_data: Dict, db) -> bool:
    """Check if this is a novel decision context we haven't seen much."""
    relationship_type = email_data.get('relationship_type', 'unknown')
    
    count = len([
        d for d in db.collection('agent_decisions')
        .where('relationship_type', '==', relationship_type)
        .limit(5)
        .stream()
    ])
    
    return count < 5


async def store_hypothesis(
    hypothesis: str,
    email_id: str,
    alternative_action: str,
    expected_outcome: str,
    email_context: Dict,
    db
) -> str:
    """Store exploration hypothesis for later validation."""
    hypothesis_doc = {
        'hypothesis': hypothesis,
        'email_id': email_id,
        'alternative_action': alternative_action,
        'expected_outcome': expected_outcome,
        'email_context': {
            'from': email_context.get('from'),
            'subject': email_context.get('subject'),
            'relationship_type': email_context.get('relationship_type'),
            'time_of_day': email_context.get('time_of_day')
        },
        'created_at': datetime.utcnow().isoformat(),
        'status': 'testing',
        'validation_result': None
    }
    
    doc_ref = db.collection('exploration_hypotheses').document()
    doc_ref.set(hypothesis_doc)
    
    return doc_ref.id
