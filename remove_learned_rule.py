#!/usr/bin/env python3
"""
Remove or deactivate learned rules that were created by mistake.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase
cred = credentials.Certificate('./firebase-service-account.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def list_learned_rules(sender_email=None):
    """List all learned rules, optionally filtered by sender."""
    print("\n🔍 Searching for learned rules...\n")

    rules_ref = db.collection('learned_rules')

    if sender_email:
        # Extract sender part (before @)
        sender_part = sender_email.split('@')[0].lower().replace('.', '').replace('_', '')
        print(f"Filtering for sender containing: {sender_part}\n")

    docs = rules_ref.stream()

    found_rules = []
    for doc in docs:
        rule = doc.to_dict()
        rule['doc_id'] = doc.id

        # Check if this rule matches the sender
        if sender_email:
            conditions = rule.get('conditions', {})
            sender_contains = conditions.get('sender_contains', '').lower()

            if sender_part not in sender_contains and sender_contains not in sender_part:
                continue

        found_rules.append(rule)

        # Display rule
        print(f"📋 Rule ID: {doc.id}")
        print(f"   Pattern: {rule.get('pattern', 'N/A')}")
        print(f"   Action: {rule.get('action', 'N/A')}")
        print(f"   Confidence: {rule.get('confidence', 0):.0%}")
        print(f"   Status: {rule.get('status', 'N/A')}")
        print(f"   Conditions: {json.dumps(rule.get('conditions', {}), indent=6)}")
        print(f"   Created: {rule.get('created_at', 'N/A')}")
        print()

    if not found_rules:
        print("No matching rules found.")

    return found_rules

def delete_rule(rule_id):
    """Permanently delete a learned rule."""
    db.collection('learned_rules').document(rule_id).delete()
    print(f"✅ Deleted rule: {rule_id}")

def deactivate_rule(rule_id):
    """Deactivate a rule (keeps it but marks as inactive)."""
    db.collection('learned_rules').document(rule_id).update({
        'status': 'inactive',
        'deactivated_at': firestore.SERVER_TIMESTAMP
    })
    print(f"✅ Deactivated rule: {rule_id}")

def main():
    import sys

    # The sender email to search for
    sender_email = "abhinav.t.ala@gmail.com"

    if len(sys.argv) > 1:
        sender_email = sys.argv[1]

    print(f"🔎 Looking for learned rules for: {sender_email}")

    rules = list_learned_rules(sender_email)

    if not rules:
        print(f"\n❌ No learned rules found for {sender_email}")
        return

    print(f"\nFound {len(rules)} rule(s) to remove.\n")

    for rule in rules:
        rule_id = rule['doc_id']
        action = rule.get('action', 'unknown')

        # Ask user for confirmation
        response = input(f"Delete rule '{rule_id}' (action: {action})? [y/N]: ").strip().lower()

        if response == 'y':
            delete_rule(rule_id)
        else:
            print(f"⏭️  Skipped: {rule_id}")

    print("\n✨ Done!")

if __name__ == '__main__':
    main()
