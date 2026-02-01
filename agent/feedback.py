"""
Feedback Module - Learning loop with Weave integration
Records feedback, updates models, and enables continuous improvement
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
async def record_feedback(
    decision_id: str,
    feedback_type: str,
    feedback_data: Dict,
    db
) -> Dict[str, Any]:
    """
    Record feedback on an agent decision.
    
    Feedback types:
    - 'action_correct': The agent's action was correct
    - 'action_wrong': The agent's action was wrong (with correction)
    - 'response_used': Generated response was used as-is
    - 'response_edited': Generated response was edited
    - 'response_discarded': Generated response was not used
    - 'importance_feedback': User indicated actual importance
    
    Args:
        decision_id: ID of the decision being evaluated
        feedback_type: Type of feedback
        feedback_data: Additional feedback details
        db: Firestore client
    
    Returns:
        Confirmation of feedback recording
    """
    feedback_record = {
        "decision_id": decision_id,
        "feedback_type": feedback_type,
        "feedback_data": feedback_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Store in training_feedback collection
    doc_ref = db.collection('training_feedback').document()
    feedback_record['id'] = doc_ref.id
    doc_ref.set(feedback_record)
    
    # Also update the original decision with feedback reference
    decision_ref = db.collection('agent_decisions').document(decision_id)
    decision_doc = decision_ref.get()
    
    if decision_doc.exists:
        decision = decision_doc.to_dict()
        decision['feedback'] = {
            "feedback_id": feedback_record['id'],
            "feedback_type": feedback_type,
            "recorded_at": datetime.utcnow().isoformat()
        }
        decision_ref.set(decision)
    
    # Trigger learning updates
    await process_feedback_for_learning(feedback_record, db)
    
    return {
        "status": "recorded",
        "feedback_id": feedback_record['id'],
        "decision_id": decision_id
    }


@weave.op()
async def process_feedback_for_learning(feedback: Dict, db) -> None:
    """
    Process feedback to improve the agent's models.
    
    CRITICAL: This validates exploration hypotheses.
    When user gives feedback on an exploration, we know if it worked.
    
    Updates:
    - Person profiles (action history)
    - Importance patterns
    - Style profiles
    - EXPLORATION HYPOTHESES (validate/reject)
    """
    feedback_type = feedback.get('feedback_type')
    feedback_data = feedback.get('feedback_data', {})
    decision_id = feedback.get('decision_id')
    
    # Get the original decision
    decision_doc = db.collection('agent_decisions').document(decision_id).get()
    if not decision_doc.exists:
        return
    
    decision = decision_doc.to_dict()
    email_id = decision.get('email_id')
    sender = decision.get('sender')
    
    # CRITICAL: Check if this was an exploration
    exploration_metadata = decision.get('exploration_metadata')
    if exploration_metadata and exploration_metadata.get('is_exploration'):
        await validate_exploration_hypothesis(
            exploration_metadata, 
            feedback_type, 
            feedback_data, 
            db
        )
    
    # Update based on feedback type
    if feedback_type == 'action_wrong':
        # Update person profile with correction
        correct_action = feedback_data.get('correct_action')
        if sender and correct_action:
            await update_person_from_feedback(sender, correct_action, db)
    
    elif feedback_type == 'importance_feedback':
        # Update importance patterns
        actual_importance = feedback_data.get('actual_importance')
        if email_id and actual_importance:
            from .importance import update_importance_model
            await update_importance_model(email_id, actual_importance, db)
    
    elif feedback_type in ['response_edited', 'response_discarded']:
        # Update style learning
        if email_id:
            from .style_learning import learn_style_from_feedback
            await learn_style_from_feedback(email_id, feedback_data.get('changes', ''), db)


@weave.op()
async def validate_exploration_hypothesis(
    exploration_metadata: Dict,
    feedback_type: str,
    feedback_data: Dict,
    db
):
    """
    Validate whether an exploration hypothesis worked.
    
    THIS IS WHERE AGENT LEARNS FROM ITS EXPERIMENTS.
    
    If exploration worked: Mark hypothesis as validated
    If exploration failed: Mark hypothesis as rejected
    """
    
    hypothesis_id = exploration_metadata.get('hypothesis_id')
    if not hypothesis_id:
        return
    
    # Determine if exploration was successful
    is_successful = (
        feedback_type == 'action_correct' or
        (feedback_type == 'action_wrong' and 
         feedback_data.get('correct_action') == exploration_metadata.get('base_decision', {}).get('action'))
    )
    
    # Update hypothesis in Firebase
    hypothesis_ref = db.collection('exploration_hypotheses').document(hypothesis_id)
    hypothesis_doc = hypothesis_ref.get()
    
    if hypothesis_doc.exists:
        hypothesis_ref.update({
            'validation_result': 'validated' if is_successful else 'rejected',
            'validated_at': datetime.utcnow().isoformat(),
            'feedback_type': feedback_type,
            'feedback_data': feedback_data
        })
        
        if is_successful:
            print(f"✅ EXPLORATION SUCCESS: Hypothesis {hypothesis_id} validated!")
        else:
            print(f"❌ EXPLORATION FAILED: Hypothesis {hypothesis_id} rejected")
    
    return {
        'hypothesis_id': hypothesis_id,
        'validation_result': 'validated' if is_successful else 'rejected',
        'is_successful': is_successful
    }


@weave.op()
async def update_person_from_feedback(sender: str, correct_action: str, db) -> None:
    """Update person profile based on action feedback."""
    from .people_graph import update_person_after_action
    await update_person_after_action(sender, correct_action, db)


@weave.op()
async def get_feedback_statistics(db, days: int = 7) -> Dict[str, Any]:
    """
    Get statistics on feedback for monitoring.
    
    Args:
        db: Firestore client
        days: Number of days to look back
    
    Returns:
        Statistics about feedback and accuracy
    """
    from datetime import timedelta
    
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # Query recent feedback
    docs = db.collection('training_feedback').where('timestamp', '>=', cutoff).stream()
    
    feedback_counts = {
        'action_correct': 0,
        'action_wrong': 0,
        'response_used': 0,
        'response_edited': 0,
        'response_discarded': 0,
        'importance_feedback': 0,
        'total': 0
    }
    
    for doc in docs:
        data = doc.to_dict()
        fb_type = data.get('feedback_type', 'unknown')
        feedback_counts[fb_type] = feedback_counts.get(fb_type, 0) + 1
        feedback_counts['total'] += 1
    
    # Calculate metrics
    total_actions = feedback_counts['action_correct'] + feedback_counts['action_wrong']
    action_accuracy = (
        feedback_counts['action_correct'] / total_actions 
        if total_actions > 0 else 0
    )
    
    total_responses = (
        feedback_counts['response_used'] + 
        feedback_counts['response_edited'] + 
        feedback_counts['response_discarded']
    )
    response_acceptance = (
        (feedback_counts['response_used'] + feedback_counts['response_edited']) / total_responses
        if total_responses > 0 else 0
    )
    
    return {
        "period_days": days,
        "feedback_counts": feedback_counts,
        "metrics": {
            "action_accuracy": action_accuracy,
            "response_acceptance_rate": response_acceptance,
            "total_feedback_items": feedback_counts['total']
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@weave.op()
async def analyze_feedback_trends(db) -> Dict[str, Any]:
    """
    Analyze feedback trends to identify areas for improvement.
    
    Uses LLM to identify patterns in feedback.
    """
    # Get recent feedback
    docs = db.collection('training_feedback').order_by(
        'timestamp', direction='DESCENDING'
    ).limit(50).stream()
    
    feedback_items = []
    for doc in docs:
        data = doc.to_dict()
        feedback_items.append({
            "type": data.get('feedback_type'),
            "data": data.get('feedback_data'),
            "timestamp": data.get('timestamp')
        })
    
    if not feedback_items:
        return {"status": "no_data", "recommendations": []}
    
    # Use LLM to analyze trends
    prompt = f"""Analyze these feedback items from an email agent and identify patterns:

{json.dumps(feedback_items[:20], indent=2)}

Identify:
1. Common types of mistakes the agent makes
2. Areas where the agent performs well
3. Specific recommendations for improvement

Respond in JSON:
{{
    "common_mistakes": ["list", "of", "mistakes"],
    "strengths": ["list", "of", "strengths"],
    "recommendations": [
        {{"area": "area name", "suggestion": "what to improve"}}
    ],
    "overall_assessment": "brief assessment"
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You analyze AI agent feedback. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(response.choices[0].message.content)
        analysis['feedback_count'] = len(feedback_items)
        analysis['analyzed_at'] = datetime.utcnow().isoformat()
        
        return analysis
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "recommendations": []
        }


@weave.op()
async def trigger_model_refresh(db) -> Dict[str, Any]:
    """
    Trigger a refresh of all learned models.
    
    Should be called periodically or when significant feedback accumulates.
    """
    results = {
        "triggered_at": datetime.utcnow().isoformat(),
        "refreshes": []
    }
    
    # Refresh importance patterns
    try:
        from .bootstrap import extract_importance_patterns, fetch_all_emails
        emails = await fetch_all_emails(db)
        patterns = await extract_importance_patterns(emails)
        db.collection('learned_patterns').document('importance').set(patterns)
        results['refreshes'].append({"type": "importance_patterns", "status": "success"})
    except Exception as e:
        results['refreshes'].append({"type": "importance_patterns", "status": "error", "error": str(e)})
    
    # Refresh communication style
    try:
        from .style_learning import analyze_communication_style
        style_result = await analyze_communication_style(db)
        results['refreshes'].append({"type": "communication_style", "status": "success"})
    except Exception as e:
        results['refreshes'].append({"type": "communication_style", "status": "error", "error": str(e)})
    
    # Refresh relationship clusters
    try:
        from .people_graph import cluster_relationships
        cluster_result = await cluster_relationships(db)
        results['refreshes'].append({"type": "relationship_clusters", "status": "success"})
    except Exception as e:
        results['refreshes'].append({"type": "relationship_clusters", "status": "error", "error": str(e)})
    
    return results


@weave.op()
async def log_weave_feedback(call_id: str, score: float, note: str = "") -> None:
    """
    Log feedback directly to Weave for model improvement tracking.
    
    Args:
        call_id: The Weave call/trace ID
        score: Score from 0-1 (1 = good, 0 = bad)
        note: Optional note about the feedback
    """
    try:
        # Get the call and add feedback
        # Note: This requires Weave's feedback API
        call = weave.ref(call_id).get()
        call.feedback.add("rating", {"score": score, "note": note})
    except Exception as e:
        print(f"⚠️ Could not log Weave feedback: {e}")
