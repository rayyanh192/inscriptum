"""
Check ACTUAL improvement from your existing Firebase data
Fast - just reads existing decisions
"""

import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('agent/.env')

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
print("📊 ANALYZING YOUR ACTUAL DATA")
print("="*70)

# Get all decisions
decisions = list(db.collection('agent_decisions').stream())

if not decisions:
    print("\n❌ No decisions found. Process some emails first!")
    exit()

print(f"\n✅ Found {len(decisions)} decisions\n")

# Analyze by sender
sender_data = defaultdict(list)

for dec in decisions:
    data = dec.to_dict()
    decision = data.get('decision', {})
    email_data = data.get('email', {})
    
    sender = email_data.get('from', 'unknown')
    confidence = decision.get('confidence', 0)
    timestamp = data.get('timestamp', '')
    
    if confidence > 0:  # Only include if has confidence
        sender_data[sender].append({
            'confidence': confidence,
            'timestamp': timestamp,
            'action': decision.get('action', 'unknown')
        })

# Find senders with multiple decisions (can show improvement)
print("🎯 CHECKING FOR IMPROVEMENT (per sender):")
print("-"*70)

found_improvement = False

for sender, decs in sender_data.items():
    if len(decs) >= 2:
        # Sort by timestamp
        decs.sort(key=lambda x: x['timestamp'])
        
        first_conf = decs[0]['confidence']
        last_conf = decs[-1]['confidence']
        improvement = (last_conf - first_conf) * 100
        
        if improvement != 0:
            found_improvement = True
            emoji = "📈" if improvement > 0 else "📉"
            print(f"\n{emoji} {sender[:40]}")
            print(f"   First email:  {first_conf*100:.0f}% confidence")
            print(f"   Latest email: {last_conf*100:.0f}% confidence")
            print(f"   Improvement:  {improvement:+.0f}%")
            print(f"   Total emails: {len(decs)}")

if not found_improvement:
    print("\n⚠️  No improvement found yet. Reasons:")
    print("   - All emails from different senders (no repeated contacts)")
    print("   - Not enough time passed")
    print("   - Need more feedback")

# Overall stats
all_confidences = [d['confidence'] for sender_decs in sender_data.values() for d in sender_decs]

if all_confidences:
    avg_conf = sum(all_confidences) / len(all_confidences)
    print(f"\n" + "="*70)
    print(f"📈 OVERALL STATS")
    print(f"="*70)
    print(f"Average Confidence: {avg_conf*100:.1f}%")
    print(f"Total Decisions: {len(all_confidences)}")
    print(f"Unique Senders: {len(sender_data)}")
    
    # Show distribution
    high = sum(1 for c in all_confidences if c >= 0.75)
    med = sum(1 for c in all_confidences if 0.5 <= c < 0.75)
    low = sum(1 for c in all_confidences if c < 0.5)
    
    print(f"\nConfidence Distribution:")
    print(f"  High (75%+):  {high} decisions")
    print(f"  Medium (50-75%): {med} decisions")
    print(f"  Low (<50%):   {low} decisions")

print("\n" + "="*70)
print("💡 TO SEE IMPROVEMENT:")
print("="*70)
print("""
1. Use the bot for a few days
2. Same senders will email you again
3. Agent will get more confident with repeated contacts
4. Run this script again to see improvement!

Current state: Baseline established ✅
Next: Wait for repeat emails from same senders
""")
