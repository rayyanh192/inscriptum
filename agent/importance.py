"""
Importance Module - Multi-signal importance prediction
Predicts email importance using learned patterns and people context
"""

import weave
from groq import Groq
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def predict_importance(email: Dict, person_context: Optional[Dict], db) -> Dict[str, Any]:
    """
    Predict the importance of an email using multiple signals.
    
    Signals used:
    1. Person importance (from people graph)
    2. Learned patterns (from bootstrap)
    3. Content analysis (urgency, action items)
    4. Gmail signals (starred, important flag)
    5. Historical behavior for this sender
    
    Args:
        email: The email to analyze
        person_context: Context about the sender (from people graph)
        db: Firestore client
    
    Returns:
        Importance prediction with score and reasoning
    """
    scores = {}
    reasoning = []
    
    # Signal 1: Person importance
    if person_context:
        person_score = person_context.get('importance_score', 0.5)
        scores['person'] = person_score
        reasoning.append(f"Sender importance: {person_score:.2f}")
    else:
        scores['person'] = 0.5  # Default for unknown senders
        reasoning.append("Unknown sender (default importance)")
    
    # Signal 2: Gmail flags
    gmail_score = calculate_gmail_signal_score(email)
    scores['gmail'] = gmail_score
    if gmail_score > 0.5:
        reasoning.append(f"Gmail signals indicate importance ({gmail_score:.2f})")
    
    # Signal 3: Learned patterns
    patterns_doc = db.collection('learned_patterns').document('importance').get()
    if patterns_doc.exists:
        patterns = patterns_doc.to_dict()
        pattern_score = apply_learned_patterns(email, patterns)
        scores['patterns'] = pattern_score
        if pattern_score != 0.5:
            reasoning.append(f"Learned patterns: {pattern_score:.2f}")
    else:
        scores['patterns'] = 0.5
    
    # Signal 4: Content urgency (LLM analysis)
    content_analysis = await analyze_content_urgency(email)
    scores['content'] = content_analysis['urgency_score']
    reasoning.append(f"Content urgency: {content_analysis['urgency_score']:.2f}")
    if content_analysis.get('action_items'):
        reasoning.append(f"Contains action items: {len(content_analysis['action_items'])}")
    
    # Signal 5: Recency factor
    recency_score = calculate_recency_score(email)
    scores['recency'] = recency_score
    
    # Weighted combination
    weights = {
        'person': 0.25,
        'gmail': 0.15,
        'patterns': 0.20,
        'content': 0.30,
        'recency': 0.10
    }
    
    final_score = sum(scores.get(k, 0.5) * w for k, w in weights.items())
    
    # Determine importance level
    if final_score >= 0.7:
        importance_level = "high"
    elif final_score >= 0.4:
        importance_level = "medium"
    else:
        importance_level = "low"
    
    return {
        "importance_score": final_score,
        "importance_level": importance_level,
        "signal_scores": scores,
        "reasoning": reasoning,
        "content_analysis": content_analysis,
        "timestamp": datetime.utcnow().isoformat()
    }


def calculate_gmail_signal_score(email: Dict) -> float:
    """Calculate importance from Gmail signals."""
    score = 0.5  # Baseline
    
    # Strong positive signals
    if email.get('is_starred', False):
        score += 0.3
    if email.get('is_important', False):
        score += 0.15
    
    # Negative signals
    if email.get('is_deleted', False):
        score -= 0.4
    if email.get('is_archived', False):
        score -= 0.1
    
    # Unread for long time = lower priority
    days_unread = email.get('days_unread')
    if days_unread and days_unread > 7:
        score -= 0.1
    
    return max(0.0, min(1.0, score))


def apply_learned_patterns(email: Dict, patterns: Dict) -> float:
    """Apply learned patterns to calculate importance."""
    score = 0.5
    rules = patterns.get('rules', [])
    
    # Extract sender domain
    sender = email.get('from', '')
    if '<' in sender:
        sender = sender.split('<')[1].split('>')[0]
    domain = sender.split('@')[-1].lower() if '@' in sender else ''
    
    for rule in rules:
        rule_type = rule.get('type', '')
        
        if rule_type == 'starred_domain_pattern':
            if domain in rule.get('domains', []):
                score += 0.15  # Domain associated with starred emails
        
        elif rule_type == 'deleted_domain_pattern':
            if domain in rule.get('domains', []):
                score -= 0.15  # Domain associated with deleted emails
    
    return max(0.0, min(1.0, score))


@weave.op()
async def analyze_content_urgency(email: Dict) -> Dict[str, Any]:
    """Analyze email content for urgency signals."""
    
    subject = email.get('subject', '')
    snippet = email.get('snippet', '')
    body = email.get('body', '')[:1000] if email.get('body') else ''
    
    content = f"Subject: {subject}\n\nContent: {snippet or body}"
    
    prompt = f"""Analyze this email for urgency and action items:

{content}

Respond in JSON with:
{{
    "urgency_score": 0.0-1.0 (how urgent is this email),
    "urgency_reason": "why this urgency level",
    "action_items": ["list", "of", "action", "items"],
    "deadline_mentioned": true/false,
    "requires_response": true/false,
    "is_time_sensitive": true/false
}}

Respond with ONLY the JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You analyze email urgency. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Content analysis error: {e}")
        return {
            "urgency_score": 0.5,
            "urgency_reason": "Unable to analyze",
            "action_items": [],
            "deadline_mentioned": False,
            "requires_response": False,
            "is_time_sensitive": False
        }


def calculate_recency_score(email: Dict) -> float:
    """Calculate importance based on email age."""
    # Get timestamp
    ts = email.get('internal_date') or email.get('timestamp')
    if not ts:
        return 0.5
    
    try:
        # Handle both string and timestamp formats
        if isinstance(ts, str):
            from dateutil import parser
            email_date = parser.parse(ts)
        else:
            email_date = datetime.fromtimestamp(ts / 1000)  # Firebase timestamps are in ms
        
        age_days = (datetime.utcnow() - email_date.replace(tzinfo=None)).days
        
        # Newer emails get higher score
        if age_days <= 1:
            return 0.8
        elif age_days <= 3:
            return 0.6
        elif age_days <= 7:
            return 0.4
        else:
            return 0.3
    except Exception:
        return 0.5


@weave.op()
async def rank_emails_by_importance(emails: List[Dict], db) -> List[Dict]:
    """
    Rank a list of emails by predicted importance.
    
    Args:
        emails: List of emails to rank
        db: Firestore client
    
    Returns:
        Emails sorted by importance (highest first)
    """
    from .people_graph import get_person_context
    
    ranked = []
    
    for email in emails:
        sender = email.get('from', '')
        person_context = await get_person_context(sender, db)
        importance = await predict_importance(email, person_context, db)
        
        email_with_importance = email.copy()
        email_with_importance['importance'] = importance
        ranked.append(email_with_importance)
    
    # Sort by importance score (highest first)
    ranked.sort(key=lambda x: x['importance']['importance_score'], reverse=True)
    
    return ranked


@weave.op()
async def update_importance_model(email_id: str, actual_importance: str, db) -> None:
    """
    Update the importance model based on feedback.
    
    Args:
        email_id: The email that was evaluated
        actual_importance: What the user indicated (high/medium/low)
        db: Firestore client
    """
    # Get current patterns
    patterns_doc = db.collection('learned_patterns').document('importance').get()
    
    if not patterns_doc.exists:
        patterns = {"rules": [], "feedback_history": []}
    else:
        patterns = patterns_doc.to_dict()
    
    # Add feedback
    feedback_history = patterns.get('feedback_history', [])
    feedback_history.append({
        "email_id": email_id,
        "actual_importance": actual_importance,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Keep last 100 feedbacks
    if len(feedback_history) > 100:
        feedback_history = feedback_history[-100:]
    
    patterns['feedback_history'] = feedback_history
    patterns['updated_at'] = datetime.utcnow().isoformat()
    
    db.collection('learned_patterns').document('importance').set(patterns)
