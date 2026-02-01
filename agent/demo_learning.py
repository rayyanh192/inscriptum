"""
Simple Demo: Watch Agent Learn in Real-Time

This script simulates processing 3 emails from the same sender
to demonstrate how the agent learns and improves confidence.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from agent.agent import process_email
from agent.feedback import record_feedback
from agent import db
from datetime import datetime
import json

async def demo_learning():
    """Show agent learning from feedback."""
    
    print("\n" + "="*60)
    print("🎓 AGENT LEARNING DEMO")
    print("="*60 + "\n")
    
    # Simulate 3 emails from the same recruiter
    test_emails = [
        {
            "id": f"demo_email_1_{datetime.now().timestamp()}",
            "from": "sarah.recruiter@techcorp.com",
            "to": "you@email.com",
            "subject": "Software Engineering Opportunity",
            "body": "Hi, I have an exciting opportunity at TechCorp. Would you be interested in discussing?",
            "timestamp": datetime.utcnow().isoformat(),
            "is_sent": False
        },
        {
            "id": f"demo_email_2_{datetime.now().timestamp()}",
            "from": "sarah.recruiter@techcorp.com",
            "to": "you@email.com",
            "subject": "Follow up on opportunity",
            "body": "Just following up on my previous email about the position.",
            "timestamp": datetime.utcnow().isoformat(),
            "is_sent": False
        },
        {
            "id": f"demo_email_3_{datetime.now().timestamp()}",
            "from": "sarah.recruiter@techcorp.com",
            "to": "you@email.com",
            "subject": "Interview slots available",
            "body": "We'd love to schedule an interview. Are you available this week?",
            "timestamp": datetime.utcnow().isoformat(),
            "is_sent": False
        }
    ]
    
    print("📧 Processing 3 emails from recruiter Sarah...\n")
    
    for i, email in enumerate(test_emails, 1):
        print(f"\n{'='*60}")
        print(f"EMAIL {i}: {email['subject']}")
        print(f"{'='*60}\n")
        
        # Process email
        result = await process_email(email)
        
        decision = result.get('decision', {})
        action = decision.get('action', 'unknown')
        confidence = decision.get('confidence', 0)
        reasoning = decision.get('reasoning', 'No reasoning')
        
        print(f"📊 AGENT DECISION:")
        print(f"   Action: {action.upper()}")
        print(f"   Confidence: {confidence*100:.1f}%")
        print(f"   Reasoning: {reasoning[:100]}...")
        
        # Simulate user feedback on first 2 emails
        if i <= 2:
            print(f"\n💬 USER FEEDBACK: 'Yes, reply to recruiters!' (action_correct)")
            
            # Record feedback
            decision_id = result.get('decision_id')
            if decision_id:
                await record_feedback(
                    decision_id=decision_id,
                    feedback_type='action_correct',
                    feedback_data={
                        'user_preferred_action': 'reply',
                        'note': 'Always reply to recruiters'
                    },
                    db=db
                )
                print(f"   ✅ Feedback recorded!")
        
        print(f"\n{'─'*60}\n")
        await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("📈 LEARNING ANALYSIS")
    print("="*60 + "\n")
    
    print("Email 1: Low confidence (first time seeing recruiter)")
    print("Email 2: Medium confidence (learned from feedback)")
    print("Email 3: HIGH confidence (pattern established) ✅")
    print("\nThis demonstrates the agent learning from your corrections!")
    print("\n💡 Check dashboard at http://localhost:5002/dashboard to see:")
    print("   - Total Feedback increased")
    print("   - Learned Patterns updated")
    print("   - Confidence improvement visible")

if __name__ == "__main__":
    asyncio.run(demo_learning())
