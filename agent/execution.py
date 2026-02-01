import weave
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import os

# Initialize Firebase if not already done
if not firebase_admin._apps:
    service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
    cred = firebase_admin.credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

@weave.op()
async def store_decision(email_id: str, email_data: dict, intent_analysis: dict, decision: dict) -> dict:
    """
    Store agent decision in Firebase 'agent_decisions' collection.
    Discord bot will read from this collection to display decisions.
    
    Args:
        email_id: Unique email identifier
        email_data: Original email data
        intent_analysis: Results from analyze_email_intent
        decision: Results from decide_action
    
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
            
            # Analysis results
            'intent': intent_analysis.get('intent'),
            'confidence': intent_analysis.get('confidence'),
            'entities': intent_analysis.get('entities', {}),
            'reasoning': intent_analysis.get('reasoning'),
            
            # Decision
            'action': decision.get('action'),
            'decision_reason': decision.get('reason'),
            'risk_level': decision.get('risk_level'),
            'suggested_response': decision.get('suggested_response'),
            
            # Metadata
            'timestamp': datetime.utcnow(),
            'processed': False,  # Discord bot will mark as True after reading
            'user_feedback': None,  # Will be updated if user provides feedback
        }
        
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
        docs = db.collection('agent_decisions') \
            .where('processed', '==', False) \
            .order_by('timestamp', direction=firestore.Query.DESCENDING) \
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
async def mark_decision_processed(decision_id: str) -> bool:
    """
    Mark a decision as processed after Discord bot displays it.
    
    Args:
        decision_id: Firebase document ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        doc_ref = db.collection('agent_decisions').document(decision_id)
        doc_ref.update({
            'processed': True,
            'processed_at': datetime.utcnow()
        })
        return True
        
    except Exception as e:
        print(f"Error marking decision as processed: {str(e)}")
        return False