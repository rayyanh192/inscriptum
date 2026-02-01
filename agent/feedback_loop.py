"""
Feedback loop for self-learning agent.
Allows you to provide feedback on agent decisions to improve over time.
"""

import asyncio
from execution import get_pending_decisions, mark_decision_processed
import firebase_admin
from firebase_admin import firestore
import os

if not firebase_admin._apps:
    service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
    cred = firebase_admin.credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

async def provide_feedback():
    """
    Interactive script to review agent decisions and provide feedback.
    This feedback can be used to improve the agent over time.
    """
    print("=" * 80)
    print("📝 AGENT FEEDBACK SYSTEM")
    print("=" * 80)
    print("Review recent agent decisions and provide feedback for improvement.\n")
    
    # Get unprocessed decisions
    decisions = await get_pending_decisions(limit=20)
    
    if not decisions:
        print("✅ No pending decisions to review!")
        return
    
    print(f"Found {len(decisions)} decision(s) to review.\n")
    
    for i, decision in enumerate(decisions, 1):
        print(f"\n{'='*80}")
        print(f"DECISION {i}/{len(decisions)}")
        print(f"{'='*80}")
        print(f"📧 From: {decision.get('from')}")
        print(f"📋 Subject: {decision.get('subject')}")
        print(f"📁 Category: {decision.get('category')}")
        print(f"🧠 Intent: {decision.get('intent')} ({decision.get('confidence', 0):.0%} confidence)")
        print(f"⚡ Agent Action: {decision.get('action')}")
        print(f"💭 Reasoning: {decision.get('reasoning', 'N/A')}")
        print(f"⚠️  Risk Level: {decision.get('risk_level', 'N/A')}")
        
        print("\nWas this decision correct?")
        print("1. ✅ Correct - Good decision")
        print("2. ⚠️  Partially Correct - Right idea, wrong execution")
        print("3. ❌ Incorrect - Wrong decision")
        print("4. ⏭️  Skip - Review later")
        print("5. 🛑 Quit - Stop reviewing")
        
        choice = input("\nYour feedback (1-5): ").strip()
        
        feedback_data = {
            'reviewed_at': firestore.SERVER_TIMESTAMP,
            'processed': True
        }
        
        if choice == '1':
            feedback_data['user_feedback'] = 'correct'
            feedback_data['feedback_rating'] = 5
            print("✅ Marked as CORRECT")
        elif choice == '2':
            feedback_data['user_feedback'] = 'partial'
            feedback_data['feedback_rating'] = 3
            better_action = input("What should the action have been? (auto/ask/notify): ").strip()
            feedback_data['suggested_action'] = better_action
            notes = input("Any additional notes? (optional): ").strip()
            if notes:
                feedback_data['feedback_notes'] = notes
            print("⚠️  Marked as PARTIALLY CORRECT")
        elif choice == '3':
            feedback_data['user_feedback'] = 'incorrect'
            feedback_data['feedback_rating'] = 1
            better_action = input("What should the action have been? (auto/ask/notify): ").strip()
            feedback_data['suggested_action'] = better_action
            notes = input("Why was it wrong? (optional): ").strip()
            if notes:
                feedback_data['feedback_notes'] = notes
            print("❌ Marked as INCORRECT")
        elif choice == '4':
            print("⏭️  Skipped")
            continue
        elif choice == '5':
            print("🛑 Stopping review session")
            break
        else:
            print("Invalid choice, skipping...")
            continue
        
        # Update Firebase with feedback
        doc_ref = db.collection('agent_decisions').document(decision['decision_id'])
        doc_ref.update(feedback_data)
    
    # Generate feedback summary
    print("\n" + "=" * 80)
    print("📊 FEEDBACK SUMMARY")
    print("=" * 80)
    
    # Get all decisions with feedback
    all_decisions = db.collection('agent_decisions') \
        .where('user_feedback', '!=', None) \
        .stream()
    
    feedback_counts = {'correct': 0, 'partial': 0, 'incorrect': 0}
    total = 0
    
    for doc in all_decisions:
        data = doc.to_dict()
        feedback = data.get('user_feedback')
        if feedback:
            feedback_counts[feedback] = feedback_counts.get(feedback, 0) + 1
            total += 1
    
    if total > 0:
        print(f"\nTotal Decisions Reviewed: {total}")
        print(f"✅ Correct: {feedback_counts['correct']} ({feedback_counts['correct']/total*100:.1f}%)")
        print(f"⚠️  Partial: {feedback_counts['partial']} ({feedback_counts['partial']/total*100:.1f}%)")
        print(f"❌ Incorrect: {feedback_counts['incorrect']} ({feedback_counts['incorrect']/total*100:.1f}%)")
        
        accuracy = (feedback_counts['correct'] + feedback_counts['partial'] * 0.5) / total * 100
        print(f"\n🎯 Overall Accuracy: {accuracy:.1f}%")
    
    print("\n💡 This feedback will be used to improve the agent's decision-making!")

if __name__ == '__main__':
    asyncio.run(provide_feedback())
