"""
Comprehensive test suite to evaluate agent decision-making.
Tests various email types and tracks decision patterns.
"""

import asyncio
import weave
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Weave with W&B
weave.init(project_name=os.getenv('WANDB_PROJECT', 'email-agent'))

from agent import handle_email
from execution import get_pending_decisions

# Test cases covering different scenarios
TEST_EMAILS = [
    {
        'id': 'test_001_newsletter',
        'data': {
            'from': 'newsletter@techcrunch.com',
            'subject': 'Top 5 AI Startups This Week',
            'body': 'Check out these amazing AI companies and their funding rounds...',
            'links': ['https://techcrunch.com/startup1', 'https://techcrunch.com/startup2'],
            'category': 'newsletter'
        },
        'expected': 'auto or notify'
    },
    {
        'id': 'test_002_urgent_action',
        'data': {
            'from': 'boss@company.com',
            'subject': 'URGENT: Review and Approve Budget by EOD',
            'body': 'Please review the attached Q1 budget proposal and approve by end of day. This is critical for our planning.',
            'links': ['https://docs.google.com/budget-q1'],
            'category': 'work'
        },
        'expected': 'ask'
    },
    {
        'id': 'test_003_phishing',
        'data': {
            'from': 'security@paypa1.com',
            'subject': 'Your Account Has Been Suspended - Act Now!',
            'body': 'Click here immediately to verify your account or it will be permanently deleted. Enter your password at this link.',
            'links': ['https://paypa1-verify.sketchy.com/login'],
            'category': 'spam'
        },
        'expected': 'notify'
    },
    {
        'id': 'test_004_meeting_request',
        'data': {
            'from': 'colleague@company.com',
            'subject': 'Coffee chat next week?',
            'body': 'Hey! Would love to catch up over coffee next week. Are you free Tuesday or Wednesday afternoon?',
            'links': [],
            'category': 'personal'
        },
        'expected': 'ask or auto'
    },
    {
        'id': 'test_005_financial',
        'data': {
            'from': 'accounting@company.com',
            'subject': 'Expense Report Reimbursement - $2,450',
            'body': 'Your expense report has been approved. The amount of $2,450 will be deposited to your account within 3 business days.',
            'links': ['https://internal.company.com/expenses/report-123'],
            'category': 'finance'
        },
        'expected': 'notify or ask'
    },
    {
        'id': 'test_006_password_reset',
        'data': {
            'from': 'noreply@github.com',
            'subject': 'Reset your password',
            'body': 'Someone requested a password reset for your account. If this was you, click the link below. Otherwise, ignore this email.',
            'links': ['https://github.com/password/reset/token-abc123'],
            'category': 'security'
        },
        'expected': 'ask'
    },
    {
        'id': 'test_007_promotion',
        'data': {
            'from': 'deals@amazon.com',
            'subject': '50% OFF - Limited Time Only!',
            'body': 'Flash sale! Get 50% off on electronics. Shop now before deals expire!',
            'links': ['https://amazon.com/deals/electronics'],
            'category': 'promotional'
        },
        'expected': 'notify'
    },
    {
        'id': 'test_008_calendar_invite',
        'data': {
            'from': 'calendar@google.com',
            'subject': 'Invitation: Team Standup @ Mon Jan 27, 2026 9am',
            'body': 'You have been invited to Team Standup on Monday, January 27, 2026 at 9:00 AM.',
            'links': ['https://calendar.google.com/event/123'],
            'category': 'calendar'
        },
        'expected': 'auto'
    }
]

async def run_comprehensive_test():
    print("=" * 80)
    print("🧪 COMPREHENSIVE AGENT DECISION TEST")
    print("=" * 80)
    print(f"Testing {len(TEST_EMAILS)} different email scenarios...\n")
    
    results = []
    
    for i, test_case in enumerate(TEST_EMAILS, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_EMAILS)}: {test_case['data']['subject']}")
        print(f"{'='*80}")
        print(f"📧 From: {test_case['data']['from']}")
        print(f"📁 Category: {test_case['data']['category']}")
        print(f"🔗 Links: {len(test_case['data']['links'])}")
        print(f"🎯 Expected: {test_case['expected']}")
        print()
        
        # Process the email
        result = await handle_email(
            email_id=test_case['id'],
            email_data=test_case['data']
        )
        
        # Store result
        test_result = {
            'test_id': test_case['id'],
            'subject': test_case['data']['subject'],
            'category': test_case['data']['category'],
            'expected': test_case['expected'],
            'actual_action': result.get('action'),
            'confidence': result.get('confidence'),
            'intent': result.get('intent'),
            'decision_id': result.get('decision_id'),
            'status': result.get('status')
        }
        results.append(test_result)
        
        # Brief pause between tests
        await asyncio.sleep(1)
    
    # Summary Report
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 80)
    
    print(f"\n{'Test ID':<25} {'Category':<15} {'Action':<10} {'Confidence':<12} {'Intent':<20}")
    print("-" * 80)
    
    for r in results:
        confidence_str = f"{r['confidence']:.0%}" if r['confidence'] else "N/A"
        print(f"{r['test_id']:<25} {r['category']:<15} {r['actual_action']:<10} {confidence_str:<12} {r['intent']:<20}")
    
    # Action Distribution
    print("\n" + "=" * 80)
    print("📈 DECISION DISTRIBUTION")
    print("=" * 80)
    
    action_counts = {}
    for r in results:
        action = r['actual_action']
        action_counts[action] = action_counts.get(action, 0) + 1
    
    for action, count in sorted(action_counts.items()):
        percentage = (count / len(results)) * 100
        bar = "█" * int(percentage / 2)
        print(f"{action:<10} {bar} {count}/{len(results)} ({percentage:.1f}%)")
    
    # Confidence Analysis
    print("\n" + "=" * 80)
    print("🎯 CONFIDENCE ANALYSIS")
    print("=" * 80)
    
    confidences = [r['confidence'] for r in results if r['confidence']]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        high_conf = sum(1 for c in confidences if c > 0.8)
        med_conf = sum(1 for c in confidences if 0.5 <= c <= 0.8)
        low_conf = sum(1 for c in confidences if c < 0.5)
        
        print(f"Average Confidence: {avg_confidence:.1%}")
        print(f"High Confidence (>80%): {high_conf}/{len(confidences)}")
        print(f"Medium Confidence (50-80%): {med_conf}/{len(confidences)}")
        print(f"Low Confidence (<50%): {low_conf}/{len(confidences)}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: {filename}")
    
    # Weave instructions
    print("\n" + "=" * 80)
    print("🔍 VIEW TRACES IN WEAVE")
    print("=" * 80)
    print("1. Go to: https://wandb.ai/")
    print("2. Navigate to your 'email-agent' project")
    print("3. View traces to see:")
    print("   - Complete email processing pipeline")
    print("   - LLM prompts and responses")
    print("   - Decision-making logic")
    print("   - Timing and performance metrics")
    
    return results

if __name__ == '__main__':
    asyncio.run(run_comprehensive_test())
