"""
Test suite for the self-learning email agent.
Run with: python -m pytest test_agent.py -v
"""

import asyncio
import weave
import os
from dotenv import load_dotenv

# Initialize Weave first
weave.init('email-agent')

load_dotenv()

# Sample test emails
TEST_EMAILS = [
    {
        "id": "test_001",
        "from": "john.smith@company.com",
        "subject": "Project deadline reminder",
        "snippet": "Hi, just a reminder that the project deadline is tomorrow. Please make sure all deliverables are submitted.",
        "body": "Hi,\n\nJust a reminder that the project deadline is tomorrow at 5 PM.\n\nPlease make sure all deliverables are submitted to the shared drive.\n\nThanks,\nJohn",
        "is_read": False,
        "is_starred": True,
        "is_archived": False,
        "is_deleted": False,
        "is_important": True,
        "has_reply": False,
        "days_unread": 0,
        "labels": ["INBOX", "IMPORTANT"],
        "category": "work"
    },
    {
        "id": "test_002",
        "from": "newsletter@marketing-company.com",
        "subject": "50% OFF - Limited Time Offer!",
        "snippet": "Don't miss our biggest sale of the year. Shop now and save!",
        "body": "MEGA SALE!\n\nGet 50% off everything!\n\nShop Now: [link]\n\nUnsubscribe: [link]",
        "is_read": True,
        "is_starred": False,
        "is_archived": True,
        "is_deleted": False,
        "is_important": False,
        "has_reply": False,
        "days_unread": None,
        "labels": ["PROMOTIONS"],
        "category": "promotions"
    },
    {
        "id": "test_003",
        "from": "mom@gmail.com",
        "subject": "Sunday dinner?",
        "snippet": "Hey! Are you free for dinner this Sunday? Dad wants to try that new Italian place.",
        "body": "Hey!\n\nAre you free for dinner this Sunday? Dad wants to try that new Italian place downtown.\n\nLet me know!\n\nLove, Mom",
        "is_read": False,
        "is_starred": True,
        "is_archived": False,
        "is_deleted": False,
        "is_important": False,
        "has_reply": True,
        "days_unread": 1,
        "labels": ["INBOX"],
        "category": "personal"
    },
    {
        "id": "test_004",
        "from": "noreply@github.com",
        "subject": "[GitHub] Your pull request was merged",
        "snippet": "Congratulations! Your pull request #123 has been merged into main.",
        "body": "Your pull request #123 has been merged.\n\nView the commit: [link]",
        "is_read": True,
        "is_starred": False,
        "is_archived": True,
        "is_deleted": False,
        "is_important": False,
        "has_reply": False,
        "days_unread": None,
        "labels": ["UPDATES"],
        "category": "notification"
    },
    {
        "id": "test_005",
        "from": "sarah.jones@startup.io",
        "subject": "Following up on our call",
        "snippet": "Great speaking with you yesterday! As discussed, here are the next steps...",
        "body": "Hi,\n\nGreat speaking with you yesterday! As discussed, here are the next steps:\n\n1. I'll send over the proposal by Friday\n2. Let's schedule a follow-up call next week\n3. Please review the attached documents\n\nLooking forward to working together!\n\nBest,\nSarah",
        "is_read": False,
        "is_starred": False,
        "is_archived": False,
        "is_deleted": False,
        "is_important": True,
        "has_reply": False,
        "days_unread": 2,
        "labels": ["INBOX", "IMPORTANT"],
        "category": "work"
    }
]


async def test_process_single_email():
    """Test processing a single email."""
    from agent import process_email, db
    
    print("\n" + "="*60)
    print("TEST: Process Single Email")
    print("="*60)
    
    result = await process_email(TEST_EMAILS[0])
    
    assert result['status'] == 'success'
    assert 'decision' in result
    assert 'importance' in result
    
    print(f"\n✅ Test passed!")
    print(f"   Intent: {result['intent']['intent']}")
    print(f"   Importance: {result['importance']['importance_level']}")
    print(f"   Decision: {result['decision']['action']}")
    
    return result


async def test_bootstrap():
    """Test the bootstrap process."""
    from agent.bootstrap import bootstrap_from_gmail_history
    from agent import db
    
    print("\n" + "="*60)
    print("TEST: Bootstrap from Gmail History")
    print("="*60)
    
    result = await bootstrap_from_gmail_history(db)
    
    print(f"\n✅ Bootstrap complete!")
    print(f"   Status: {result['status']}")
    print(f"   People created: {result.get('people_created', 0)}")
    print(f"   Patterns learned: {result.get('patterns_learned', 0)}")
    
    return result


async def test_people_graph():
    """Test the people graph functionality."""
    from agent.people_graph import analyze_person, cluster_relationships
    from agent import db
    
    print("\n" + "="*60)
    print("TEST: People Graph")
    print("="*60)
    
    # Test analyzing a person
    profile = await analyze_person(
        "john.smith@company.com",
        [TEST_EMAILS[0]],
        db
    )
    
    print(f"\n✅ Person profile created!")
    print(f"   Email: {profile['email']}")
    print(f"   Importance: {profile.get('importance_score', 0):.2f}")
    print(f"   Relationship: {profile.get('relationship', {}).get('type', 'unknown')}")
    
    # Test clustering
    clusters = await cluster_relationships(db)
    
    print(f"\n✅ Clustering complete!")
    print(f"   Total clusters: {clusters.get('total_clusters', 0)}")
    
    return profile, clusters


async def test_importance_prediction():
    """Test importance prediction."""
    from agent.importance import predict_importance
    from agent.people_graph import get_person_context
    from agent import db
    
    print("\n" + "="*60)
    print("TEST: Importance Prediction")
    print("="*60)
    
    email = TEST_EMAILS[0]
    person_context = await get_person_context(email['from'], db)
    importance = await predict_importance(email, person_context, db)
    
    print(f"\n✅ Importance predicted!")
    print(f"   Score: {importance['importance_score']:.2f}")
    print(f"   Level: {importance['importance_level']}")
    print(f"   Reasoning: {importance['reasoning'][:2]}")
    
    return importance


async def test_style_learning():
    """Test communication style learning."""
    from agent.style_learning import analyze_communication_style, get_style_for_recipient
    from agent import db
    
    print("\n" + "="*60)
    print("TEST: Style Learning")
    print("="*60)
    
    # This may return insufficient data if no replied emails
    result = await analyze_communication_style(db)
    
    print(f"\n✅ Style analysis complete!")
    print(f"   Status: {result['status']}")
    if result['status'] == 'success':
        style = result['style_profile']
        print(f"   Formality: {style.get('formality_level', 'unknown')}")
        print(f"   Tone: {style.get('tone', 'unknown')}")
    
    return result


async def test_response_generation():
    """Test response generation."""
    from agent.response_generator import generate_contextual_response, generate_quick_replies
    from agent.people_graph import get_person_context
    from agent.importance import predict_importance
    from agent.style_learning import get_style_for_recipient
    from agent import db
    
    print("\n" + "="*60)
    print("TEST: Response Generation")
    print("="*60)
    
    email = TEST_EMAILS[4]  # The follow-up email
    
    person_context = await get_person_context(email['from'], db)
    importance = await predict_importance(email, person_context, db)
    style = await get_style_for_recipient(email['from'], db)
    
    response = await generate_contextual_response(
        email, person_context, importance, style, db
    )
    
    print(f"\n✅ Response generated!")
    print(f"   Subject: {response['subject']}")
    print(f"   Body preview: {response['body'][:100]}...")
    
    # Test quick replies
    quick_replies = await generate_quick_replies(email, person_context, db)
    
    print(f"\n✅ Quick replies generated: {len(quick_replies)}")
    for qr in quick_replies:
        print(f"   - {qr['type']}: {qr['text'][:50]}...")
    
    return response, quick_replies


async def test_full_pipeline():
    """Test the full email processing pipeline."""
    from agent import process_inbox, initialize_agent, get_agent_status
    
    print("\n" + "="*60)
    print("TEST: Full Pipeline")
    print("="*60)
    
    # Get initial status
    status = await get_agent_status()
    print(f"\n📊 Initial agent status:")
    print(f"   People profiles: {status['statistics']['people_profiles']}")
    print(f"   Emails analyzed: {status['statistics']['emails_analyzed']}")
    print(f"   Decisions made: {status['statistics']['decisions_made']}")
    
    return status


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 RUNNING ALL TESTS")
    print("="*60)
    
    results = {}
    
    try:
        results['bootstrap'] = await test_bootstrap()
    except Exception as e:
        print(f"❌ Bootstrap test failed: {e}")
        results['bootstrap'] = None
    
    try:
        results['people_graph'] = await test_people_graph()
    except Exception as e:
        print(f"❌ People graph test failed: {e}")
        results['people_graph'] = None
    
    try:
        results['importance'] = await test_importance_prediction()
    except Exception as e:
        print(f"❌ Importance test failed: {e}")
        results['importance'] = None
    
    try:
        results['style'] = await test_style_learning()
    except Exception as e:
        print(f"❌ Style learning test failed: {e}")
        results['style'] = None
    
    try:
        results['response'] = await test_response_generation()
    except Exception as e:
        print(f"❌ Response generation test failed: {e}")
        results['response'] = None
    
    try:
        results['single_email'] = await test_process_single_email()
    except Exception as e:
        print(f"❌ Single email test failed: {e}")
        results['single_email'] = None
    
    try:
        results['full_pipeline'] = await test_full_pipeline()
    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        results['full_pipeline'] = None
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is not None)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result is not None else "❌"
        print(f"   {status} {name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
