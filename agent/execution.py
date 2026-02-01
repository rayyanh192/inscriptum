"""
Execution Module - Firebase operations for storing and retrieving decisions
Enhanced with people context and generated responses
"""

import weave
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import shared db from package
from . import db


@weave.op()
async def store_decision(
    email_id: str,
    email_data: dict,
    intent_analysis: dict,
    decision: dict,
    importance: Optional[Dict] = None,
    person_context: Optional[Dict] = None,
    generated_response: Optional[Dict] = None,
    automation_context: Optional[Dict] = None
) -> dict:
    """
    Store agent decision in Firebase 'agent_decisions' collection.
    Discord bot will read from this collection to display decisions.
    
    Enhanced to include:
    - Importance prediction
    - Person context
    - Generated responses
    
    Args:
        email_id: Unique email identifier
        email_data: Original email data
        intent_analysis: Results from analyze_email_intent
        decision: Results from decide_action
        importance: Optional importance prediction
        person_context: Optional person context
        generated_response: Optional generated response
        automation_context: Optional automation context/state
    
    Returns:
        Dictionary with decision_id and timestamp
    """
    try:
        decision_data = {
            # Email info
            'email_id': email_id,
            'from': email_data.get('from'),
            'subject': email_data.get('subject'),
            'category': email_data.get('category'),
            'link_count': len(email_data.get('links', [])),
            
            # Behavior signals (from scraper)
            'is_read': email_data.get('is_read', False),
            'is_starred': email_data.get('is_starred', False),
            'is_archived': email_data.get('is_archived', False),
            'is_deleted': email_data.get('is_deleted', False),
            'has_reply': email_data.get('has_reply', False),
            'days_unread': email_data.get('days_unread'),
            
            # Analysis results
            'intent': intent_analysis.get('intent'),
            'confidence': intent_analysis.get('confidence'),
            'entities': intent_analysis.get('entities', {}),
            'reasoning': intent_analysis.get('reasoning'),
            
            # Decision
            'action': decision.get('action'),
            'decision_reason': decision.get('reason'),
            'risk_level': decision.get('risk_level'),
            'priority': decision.get('priority', 'medium'),
            'suggested_response': decision.get('suggested_response'),
            
            # Metadata
            'timestamp': datetime.utcnow(),
            'processed': False,  # Discord bot will mark as True after reading
            'user_feedback': None,  # Will be updated if user provides feedback
        }
        
        # Add importance if provided
        if importance:
            decision_data['importance'] = {
                'score': importance.get('importance_score'),
                'level': importance.get('importance_level'),
                'reasoning': importance.get('reasoning', [])
            }
        
        # Add person context summary if provided
        if person_context:
            decision_data['person'] = {
                'name': person_context.get('name'),
                'email': person_context.get('email'),
                'importance_score': person_context.get('importance_score'),
                'relationship_type': person_context.get('relationship', {}).get('type'),
                'relationship_category': person_context.get('relationship', {}).get('category'),
                'total_interactions': person_context.get('total_interactions', 0)
            }
        
        # Add generated response if provided
        if generated_response:
            decision_data['generated_response'] = {
                'id': generated_response.get('id'),
                'subject': generated_response.get('subject'),
                'body': generated_response.get('body'),
                'key_points': generated_response.get('key_points_addressed', [])
            }

        # Add automation context if provided
        if automation_context:
            decision_data['automation_context'] = automation_context
        
        # Store in Firebase
        doc_ref = db.collection('agent_decisions').document()
        doc_ref.set(decision_data)
        
        return {
            'status': 'success',
            'decision_id': doc_ref.id,
            'timestamp': decision_data['timestamp'].isoformat()
        }
        
    except Exception as e:
        print(f"Error storing decision: {str(e)}")
        raise


@weave.op()
async def get_pending_decisions(limit: int = 10) -> list:
    """
    Retrieve unprocessed decisions from Firebase.
    Useful for Discord bot to poll for new decisions.
    
    Args:
        limit: Maximum number of decisions to retrieve
    
    Returns:
        List of decision dictionaries
    """
    try:
        from google.cloud.firestore import Query
        
        docs = db.collection('agent_decisions') \
            .where('processed', '==', False) \
            .order_by('timestamp', direction=Query.DESCENDING) \
            .limit(limit) \
            .stream()
        
        decisions = []
        for doc in docs:
            data = doc.to_dict()
            data['decision_id'] = doc.id
            decisions.append(data)
        
        return decisions
        
    except Exception as e:
        print(f"Error retrieving pending decisions: {str(e)}")
        return []


@weave.op()
async def mark_decision_processed(decision_id: str, feedback: Optional[Dict] = None) -> bool:
    """
    Mark a decision as processed after Discord bot displays it.
    
    Args:
        decision_id: Firebase document ID
        feedback: Optional feedback from user
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc_ref = db.collection('agent_decisions').document(decision_id)
        
        update_data = {
            'processed': True,
            'processed_at': datetime.utcnow()
        }
        
        if feedback:
            update_data['user_feedback'] = feedback
        
        doc_ref.update(update_data)
        return True
        
    except Exception as e:
        print(f"Error marking decision as processed: {str(e)}")
        return False


@weave.op()
async def get_decision_by_id(decision_id: str) -> Optional[Dict]:
    """Get a specific decision by ID."""
    try:
        doc = db.collection('agent_decisions').document(decision_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['decision_id'] = doc.id
            return data
        return None
    except Exception as e:
        print(f"Error getting decision: {str(e)}")
        return None


@weave.op()
async def get_decisions_for_email(email_id: str) -> List[Dict]:
    """Get all decisions for a specific email."""
    try:
        docs = db.collection('agent_decisions') \
            .where('email_id', '==', email_id) \
            .stream()
        
        decisions = []
        for doc in docs:
            data = doc.to_dict()
            data['decision_id'] = doc.id
            decisions.append(data)
        
        return decisions
    except Exception as e:
        print(f"Error getting decisions for email: {str(e)}")
        return []


@weave.op()
async def update_decision_feedback(decision_id: str, feedback: Dict) -> bool:
    """
    Update the feedback on a decision.
    
    Args:
        decision_id: Firebase document ID
        feedback: Feedback data (action_correct, actual_action, notes, etc.)
    
    Returns:
        True if successful
    """
    try:
        doc_ref = db.collection('agent_decisions').document(decision_id)
        
        doc_ref.update({
            'user_feedback': {
                **feedback,
                'feedback_at': datetime.utcnow()
            }
        })
        
        # Also trigger feedback learning
        from .feedback import record_feedback
        
        feedback_type = 'action_correct' if feedback.get('correct', True) else 'action_wrong'
        await record_feedback(
            decision_id=decision_id,
            feedback_type=feedback_type,
            feedback_data=feedback,
            db=db
        )
        
        return True
        
    except Exception as e:
        print(f"Error updating decision feedback: {str(e)}")
        return False
