#!/usr/bin/env python3
"""
Check the state of the email agent - rules, people, and importance scores.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase
cred = credentials.Certificate('./firebase-service-account.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_learned_rules():
    """List all learned rules."""
    print("\n📚 LEARNED RULES\n" + "="*50)

    rules = db.collection('learned_rules').stream()
    count = 0

    for doc in rules:
        rule = doc.to_dict()
        count += 1
        print(f"\n{count}. Rule ID: {doc.id}")
        print(f"   Pattern: {rule.get('pattern', 'N/A')}")
        print(f"   Action: {rule.get('action', 'N/A')}")
        print(f"   Confidence: {rule.get('confidence', 0):.0%}")
        print(f"   Status: {rule.get('status', 'active')}")
        print(f"   Conditions: {json.dumps(rule.get('conditions', {}))}")

    if count == 0:
        print("No learned rules found.")
    else:
        print(f"\nTotal: {count} rules")

def check_people(email_filter=None):
    """List person profiles."""
    print("\n👥 PEOPLE PROFILES\n" + "="*50)

    people = db.collection('people').stream()
    count = 0

    for doc in people:
        person = doc.to_dict()
        email = person.get('email', '')

        # Filter if requested
        if email_filter and email_filter.lower() not in email.lower():
            continue

        count += 1
        importance = person.get('importance_score', 0.5)

        print(f"\n{count}. ID: {doc.id}")
        print(f"   Email: {email}")
        print(f"   Importance: {importance:.2f}")
        print(f"   Signals: starred={person.get('behavior_signal_starred', False)}, "
              f"deleted={person.get('behavior_signal_deleted', False)}, "
              f"replied={person.get('behavior_signal_replied', False)}")
        print(f"   Last update: {person.get('last_behavior_update', 'N/A')}")

    if count == 0:
        print("No people profiles found.")
    else:
        print(f"\nTotal: {count} profiles")

def check_recent_decisions(limit=10):
    """Show recent agent decisions."""
    print(f"\n🤖 RECENT DECISIONS (last {limit})\n" + "="*50)

    decisions = db.collection('agent_decisions')\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(limit)\
        .stream()

    count = 0
    for doc in decisions:
        dec = doc.to_dict()
        count += 1

        print(f"\n{count}. From: {dec.get('sender', 'N/A')}")
        print(f"   Subject: {dec.get('subject', 'N/A')[:60]}")
        print(f"   Action: {dec.get('decision', {}).get('action', 'N/A')}")
        print(f"   Confidence: {dec.get('decision', {}).get('confidence', 0):.0%}")
        print(f"   Is Learned: {dec.get('decision', {}).get('is_learned', False)}")
        print(f"   Time: {dec.get('timestamp', 'N/A')}")

    if count == 0:
        print("No recent decisions found.")

def main():
    import sys

    email_filter = "abhinav.t.ala@gmail.com" if len(sys.argv) == 1 else sys.argv[1] if len(sys.argv) > 1 else None

    print("🔍 INSCRIPTUM AGENT STATE CHECK")
    print("="*50)

    check_learned_rules()
    check_people(email_filter)
    check_recent_decisions(5)

    print("\n" + "="*50)
    print("✅ Check complete!")

if __name__ == '__main__':
    main()
