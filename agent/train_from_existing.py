"""
Train agent from existing email actions.
Learns from what you ACTUALLY did with emails.
"""

import sys
sys.path.insert(0, '.')

import os
from dotenv import load_dotenv
load_dotenv('.env')
if not os.getenv('GROQ_API_KEY'):
    load_dotenv('agent/.env')
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

def train_from_existing_emails():
    """Learn from what you actually did with emails."""
    
    print("=" * 70)
    print("🎓 TRAINING FROM EXISTING EMAIL ACTIONS")
    print("=" * 70)
    
    # Get all emails
    emails = list(db.collection('emails').limit(100).stream())
    print(f"\n📧 Found {len(emails)} emails")
    
    training_examples = []
    
    for email in emails:
        data = email.to_dict()
        email_id = email.id
        
        # Determine ground truth action from your behavior
        ground_truth = None
        
        if data.get('replied'):
            ground_truth = 'respond'
        elif data.get('is_trashed'):
            ground_truth = 'delete'
        elif data.get('is_starred'):
            ground_truth = 'star'
        elif data.get('is_read') and data.get('days_unread', 0) > 7:
            ground_truth = 'archive'
        elif not data.get('is_read') and data.get('days_unread', 0) > 3:
            ground_truth = 'archive'
        
        if ground_truth:
            training_examples.append({
                'email_id': email_id,
                'from': data.get('from', ''),
                'subject': data.get('subject', ''),
                'action': ground_truth,
                'your_action': True
            })
    
    print(f"✅ Created {len(training_examples)} training examples\n")
    
    # Group by action
    action_counts = {}
    for ex in training_examples:
        action = ex['action']
        action_counts[action] = action_counts.get(action, 0) + 1
    
    print("📊 Training data breakdown:")
    for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {action}: {count} examples")
    
    # Save as learned patterns
    if training_examples:
        pattern_doc = {
            'trained_at': datetime.utcnow().isoformat(),
            'num_examples': len(training_examples),
            'examples': training_examples[:20],  # Store sample
            'action_distribution': action_counts
        }
        
        db.collection('learned_patterns').document('trained_from_existing').set(pattern_doc)
        print(f"\n💾 Saved training patterns to Firebase")
        print(f"✅ Agent is now trained on {len(training_examples)} real examples!")
    else:
        print("\n❌ No training examples found. Process more emails first.")
    
    return training_examples

if __name__ == "__main__":
    examples = train_from_existing_emails()
    print(f"\n🎯 Next step: Run evaluation WITH learned context")
    print(f"   python agent/eval_with_learning.py")
