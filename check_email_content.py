#!/usr/bin/env python3
"""
Check the actual content of recent emails to debug link extraction.
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase
cred = credentials.Certificate('./firebase-service-account.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_recent_emails(sender_filter=None, limit=5):
    """Check recent emails to see their actual content."""
    print("\n📧 RECENT EMAIL CONTENT\n" + "="*60)

    query = db.collection('emails').order_by('timestamp', direction=firestore.Query.DESCENDING)

    if sender_filter:
        # Note: Firestore needs an index for this combined query
        # For now, we'll filter in code
        emails = query.limit(50).stream()
    else:
        emails = query.limit(limit).stream()

    count = 0
    for doc in emails:
        email = doc.to_dict()
        sender = email.get('from', '')

        # Apply sender filter if specified
        if sender_filter and sender_filter.lower() not in sender.lower():
            continue

        count += 1
        if count > limit:
            break

        print(f"\n{count}. Subject: {email.get('subject', 'N/A')}")
        print(f"   From: {sender}")
        print(f"   ID: {doc.id}")

        body = email.get('body', '')
        links = email.get('links', [])

        print(f"   Body (first 200 chars):")
        print(f"   {repr(body[:200])}")
        print(f"   Links found: {len(links)}")
        if links:
            for i, link in enumerate(links[:5], 1):
                print(f"      {i}. {link}")
        else:
            print(f"      (no links)")

        print(f"   Timestamp: {email.get('date', 'N/A')}")

    if count == 0:
        print("No matching emails found.")
    else:
        print(f"\nTotal: {count} emails")

def main():
    import sys
    sender = "abhinav.t.ala@gmail.com" if len(sys.argv) == 1 else sys.argv[1] if len(sys.argv) > 1 else None
    check_recent_emails(sender, limit=10)

if __name__ == '__main__':
    main()
