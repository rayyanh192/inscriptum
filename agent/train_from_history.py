"""
Train Agent from Historical Email Actions

Infers correct actions from what you ACTUALLY did:
- Responded → should "respond"
- Trashed → should "delete"  
- Starred → should "star"
- Left unread 7+ days → should "archive"
- Opened/read quickly → should "notify"
"""

import sys
sys.path.insert(0, '.')

import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

load_dotenv('.env')
if not os.getenv('GROQ_API_KEY'):
    load_dotenv('agent/.env')

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def infer_correct_action(email_data):
    """
    Infer what the correct action should have been based on user behavior.
    """
    # Check if trashed
    if email_data.get('is_trashed') or email_data.get('trashed'):
        return 'delete', 1.0, 'User trashed this email'
    
    # Check if starred
    if email_data.get('is_starred') or email_data.get('starred'):
        return 'star', 1.0, 'User starred this email'
    
    # Check if replied to (look for reply indicators)
    labels = email_data.get('labels', [])
    if 'SENT' in labels or email_data.get('replied_to'):
        return 'respond', 1.0, 'User responded to this email'
    
    # Check if left unread for long time (low priority → archive)
    days_unread = email_data.get('days_unread', 0)
    if days_unread >= 7:
        return 'archive', 0.9, f'Left unread for {days_unread} days - likely low priority'
    
    # If read quickly and not acted on → FYI only
    is_read = email_data.get('is_read', False)
    if is_read and days_unread < 1:
        return 'notify', 0.7, 'Read quickly but no action taken - FYI only'
    
    # Default: uncertain
    return None, 0, 'Cannot infer action from behavior'

def create_training_feedback(email_data, decision_id):
    """
    Create training feedback entry from historical email.
    """
    correct_action, confidence, reasoning = infer_correct_action(email_data)
    
    if not correct_action:
        return None
    
    feedback = {
        'decision_id': decision_id,
        'email_id': email_data.get('id'),
        'correct_action': correct_action,
        'feedback_type': 'inferred_from_history',
        'confidence': confidence,
        'reasoning': reasoning,
        'timestamp': datetime.utcnow(),
        'sender': email_data.get('from', 'unknown'),
        'subject': email_data.get('subject', 'No subject')[:100]
    }
    
    return feedback

def train_from_history(limit=50):
    """
    Load historical emails and create training data.
    """
    print("=" * 70)
    print("🎓 TRAINING FROM HISTORICAL EMAIL ACTIONS")
    print("=" * 70)
    
    # Get emails from Firebase
    print(f"\n📧 Loading up to {limit} emails from Firebase...")
    emails = list(db.collection('emails').limit(limit).stream())
    
    print(f"   Found {len(emails)} emails\n")
    
    training_count = 0
    skipped_count = 0
    
    for doc in emails:
        email_data = doc.to_dict()
        email_id = email_data.get('id', doc.id)
        
        # Check if we already have a decision for this email
        decision_query = db.collection('agent_decisions').where('email_id', '==', email_id).limit(1).stream()
        decision_docs = list(decision_query)
        
        if not decision_docs:
            # No decision yet - skip
            skipped_count += 1
            continue
        
        decision_doc = decision_docs[0]
        decision_id = decision_doc.id
        decision_data = decision_doc.to_dict()
        
        # Infer correct action
        feedback = create_training_feedback(email_data, decision_id)
        
        if not feedback:
            skipped_count += 1
            continue
        
        # Check if feedback already exists
        existing = list(db.collection('training_feedback')
                       .where('decision_id', '==', decision_id)
                       .where('feedback_type', '==', 'inferred_from_history')
                       .limit(1).stream())
        
        if existing:
            skipped_count += 1
            continue
        
        # Store training feedback
        db.collection('training_feedback').add(feedback)
        
        training_count += 1
        
        # Show progress
        action_predicted = decision_data.get('action', 'unknown')
        action_correct = feedback['correct_action']
        match = '✅' if action_predicted == action_correct else '❌'
        
        print(f"{match} {email_data.get('subject', 'No subject')[:60]}")
        print(f"   From: {email_data.get('from', 'unknown')[:50]}")
        print(f"   Predicted: {action_predicted} | Correct: {action_correct}")
        print(f"   Reason: {feedback['reasoning'][:80]}")
        print()
    
    print("=" * 70)
    print("📊 TRAINING COMPLETE")
    print("=" * 70)
    print(f"✅ Created {training_count} training examples")
    print(f"⏭️  Skipped {skipped_count} emails (no clear action or already trained)")
    print(f"\n💡 Agent now has {training_count} real examples to learn from!")
    print("   Run eval_fast.py again to see improvement!")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    train_from_history(limit)
