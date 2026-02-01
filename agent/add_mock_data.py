"""
Add mock email data to Firebase - bypass quota issues
"""

import sys
sys.path.insert(0, '.')

import os
from dotenv import load_dotenv
load_dotenv('.env')

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Mock emails based on realistic patterns
mock_emails = [
    # Boss/urgent emails
    {"from": "sarah.chen@techcorp.com", "subject": "URGENT: Board presentation needed by EOD", "body": "Can you please finish the slides? Board meeting is tomorrow.", "is_read": False, "is_starred": True, "replied": False, "days_unread": 0},
    {"from": "john.manager@techcorp.com", "subject": "Re: Q4 Budget Review", "body": "Thanks for the update. Let's discuss tomorrow.", "is_read": True, "is_starred": False, "replied": True, "days_unread": 0},
    
    # Client emails
    {"from": "client@bigcorp.com", "subject": "Project timeline concerns", "body": "We're worried about the deadline. Can we schedule a call?", "is_read": False, "is_starred": True, "replied": False, "days_unread": 1},
    {"from": "support@clientcompany.com", "subject": "Re: Invoice #1234", "body": "Payment has been processed.", "is_read": True, "is_starred": False, "replied": False, "days_unread": 0},
    
    # Newsletters/marketing (should archive/delete)
    {"from": "newsletter@techcrunch.com", "subject": "This Week in Tech - Jan 2026", "body": "Top stories this week...", "is_read": False, "is_starred": False, "replied": False, "days_unread": 5},
    {"from": "promotions@retailstore.com", "subject": "50% OFF SALE THIS WEEKEND!", "body": "Don't miss out on huge savings...", "is_read": False, "is_starred": False, "replied": False, "days_unread": 10},
    {"from": "marketing@saascompany.com", "subject": "Webinar: Boost Your Productivity", "body": "Join us for a free webinar...", "is_read": False, "is_starred": False, "replied": False, "days_unread": 7},
    
    # Spam (should delete)
    {"from": "winner@lottery-scam.com", "subject": "YOU'VE WON $10,000!!!", "body": "Click here to claim your prize now!!!", "is_read": False, "is_starred": False, "replied": False, "days_unread": 2, "is_trashed": True},
    {"from": "phishing@fake-bank.com", "subject": "Urgent: Verify your account", "body": "Your account will be suspended unless you click here...", "is_read": False, "is_starred": False, "replied": False, "days_unread": 1, "is_trashed": True},
    
    # Team updates (FYI/notify)
    {"from": "team@techcorp.com", "subject": "Office closed for maintenance tomorrow", "body": "Heads up - office will be closed.", "is_read": True, "is_starred": False, "replied": False, "days_unread": 0},
    {"from": "hr@techcorp.com", "subject": "New parking policy starting next month", "body": "Please review the updated parking guidelines...", "is_read": False, "is_starred": False, "replied": False, "days_unread": 3},
    
    # Automated/receipts (archive)
    {"from": "noreply@github.com", "subject": "Your pull request was merged", "body": "PR #123 has been merged into main.", "is_read": True, "is_starred": False, "replied": False, "days_unread": 0},
    {"from": "receipts@amazon.com", "subject": "Your order has shipped", "body": "Track your package...", "is_read": True, "is_starred": False, "replied": False, "days_unread": 0},
    
    # Personal/friends (respond or archive depending on urgency)
    {"from": "friend@gmail.com", "subject": "Lunch this weekend?", "body": "Want to grab lunch on Saturday?", "is_read": False, "is_starred": False, "replied": False, "days_unread": 2},
    {"from": "mom@family.com", "subject": "How are you doing?", "body": "Haven't heard from you in a while...", "is_read": False, "is_starred": True, "replied": False, "days_unread": 4},
]

print("=" * 70)
print("🎭 ADDING MOCK EMAIL DATA")
print("=" * 70)

added = 0
for i, email in enumerate(mock_emails, 1):
    # Add standard fields
    email['id'] = f"mock_{i}_{random.randint(1000, 9999)}"
    email['timestamp'] = (datetime.utcnow() - timedelta(days=email.get('days_unread', 0))).isoformat()
    email['snippet'] = email['body'][:100]
    
    # Save to Firebase
    db.collection('emails').document(email['id']).set(email)
    added += 1
    
    # Determine expected action based on behavior
    action = "ask"
    if email.get('replied'):
        action = "respond"
    elif email.get('is_trashed'):
        action = "delete"
    elif email.get('is_starred'):
        action = "star" if not email.get('replied') else "respond"
    elif email.get('is_read') and email.get('days_unread', 0) > 5:
        action = "archive"
    elif not email.get('is_read') and email.get('days_unread', 0) > 7:
        action = "archive"
    
    print(f"  {i:2d}. {email['from'][:30]:30s} → {action:10s} ({email['subject'][:40]})")

print(f"\n✅ Added {added} mock emails to Firebase")
print(f"💡 Now run: python agent/train_from_existing.py")
