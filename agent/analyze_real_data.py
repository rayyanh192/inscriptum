"""
Quick Analysis: Show REAL Improvement from Your Existing Data

Analyzes your 100 decisions in Firebase to find actual learning patterns.
"""

import sys
sys.path.insert(0, '.')

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from collections import defaultdict

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

print("\n" + "="*70)
print("📊 REAL DATA ANALYSIS - Your Existing Decisions")
print("="*70)

# Get all decisions
decisions = list(db.collection('agent_decisions').stream())

print(f"\n📧 Total Decisions: {len(decisions)}")

if len(decisions) < 10:
    print("\n⚠️  Not enough data yet. Need at least 10 decisions.")
    print("   Run the bot for a while to collect more data.")
    exit()

# Parse decisions
parsed = []
for dec in decisions:
    data = dec.to_dict()
    decision = data.get('decision', {})
    
    timestamp = data.get('timestamp')
    if timestamp and isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', ''))
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    parsed.append({
        'id': dec.id,
        'timestamp': dt,
        'action': decision.get('action', 'unknown'),
        'confidence': decision.get('confidence', 0),
        'email_from': data.get('email', {}).get('from', 'unknown'),
        'has_feedback': 'feedback' in data
    })

# Sort by timestamp
parsed.sort(key=lambda x: x['timestamp'])

print("\n" + "="*70)
print("📈 CONFIDENCE TREND ANALYSIS")
print("="*70)

# Split into early vs late decisions
split_point = len(parsed) // 2
early = parsed[:split_point]
late = parsed[split_point:]

early_conf = [d['confidence'] for d in early if d['confidence'] > 0]
late_conf = [d['confidence'] for d in late if d['confidence'] > 0]

if early_conf and late_conf:
    early_avg = sum(early_conf) / len(early_conf)
    late_avg = sum(late_conf) / len(late_conf)
    improvement = late_avg - early_avg
    
    print(f"\nFirst {len(early)} decisions:")
    print(f"  Average Confidence: {early_avg*100:.1f}%")
    print(f"  Range: {min(early_conf)*100:.0f}% - {max(early_conf)*100:.0f}%")
    
    print(f"\nLast {len(late)} decisions:")
    print(f"  Average Confidence: {late_avg*100:.1f}%")
    print(f"  Range: {min(late_conf)*100:.0f}% - {max(late_conf)*100:.0f}%")
    
    if improvement > 0:
        print(f"\n✅ IMPROVEMENT: +{improvement*100:.1f}%")
        print("   Agent IS learning!")
    elif improvement < 0:
        print(f"\n📊 Change: {improvement*100:.1f}%")
        print("   Agent needs more feedback")
    else:
        print(f"\n📊 No change yet")
        print("   Agent needs more varied data")
else:
    print("\n⚠️  No confidence data found in decisions")
    print("   This is why Weave shows N/A")

print("\n" + "="*70)
print("👥 PER-SENDER LEARNING")
print("="*70)

# Group by sender
sender_decisions = defaultdict(list)
for d in parsed:
    sender_decisions[d['email_from']].append(d)

# Find senders with multiple emails
multi_email_senders = {
    sender: decisions 
    for sender, decisions in sender_decisions.items() 
    if len(decisions) >= 3
}

if multi_email_senders:
    print(f"\nFound {len(multi_email_senders)} senders with 3+ emails:")
    
    for sender, decisions in list(multi_email_senders.items())[:5]:
        decisions.sort(key=lambda x: x['timestamp'])
        confidences = [d['confidence'] for d in decisions if d['confidence'] > 0]
        
        if len(confidences) >= 2:
            first = confidences[0]
            last = confidences[-1]
            change = last - first
            
            status = "✅" if change > 0.1 else "📊"
            print(f"\n{status} {sender[:40]}")
            print(f"   Emails: {len(decisions)}")
            print(f"   First: {first*100:.0f}% → Last: {last*100:.0f}%")
            if change > 0:
                print(f"   Improvement: +{change*100:.0f}%")
else:
    print("\nNeed more emails from same senders to see learning")

print("\n" + "="*70)
print("🎯 FEEDBACK ANALYSIS")
print("="*70)

with_feedback = [d for d in parsed if d['has_feedback']]
print(f"\nDecisions with feedback: {len(with_feedback)}/{len(parsed)}")

if with_feedback:
    print("\nThis feedback is training the agent!")
    print("Give more feedback to see better improvement.")

print("\n" + "="*70)
print("💡 SUMMARY")
print("="*70)

if early_conf and late_conf and improvement > 0.05:
    print(f"\n✅ Agent IS learning! (+{improvement*100:.1f}% confidence)")
    print("   Keep using it and giving feedback.")
elif not early_conf or not late_conf:
    print("\n⚠️  Confidence data missing (showing N/A in Weave)")
    print("   Issue: Agent not recording confidence properly")
    print("   Check agent/agent.py decision output format")
else:
    print("\n📊 Not enough data yet to show clear improvement")
    print(f"   Current: {len(parsed)} decisions")
    print("   Need: 50+ decisions over multiple days")
    print("   With: Feedback on 20+ decisions")

print()
