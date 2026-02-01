"""
Generate synthetic emails for testing the email agent.
Writes directly to Firebase emails/ collection.
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta
from typing import List, Dict
import weave
from dotenv import load_dotenv
load_dotenv('agent/.env')

# Add parent directory to path
sys.path.insert(0, '.')

# Import Firebase after path adjustment
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized!")

db = firestore.client()

# Email templates by category
SYNTHETIC_EMAILS = [
    # Personal friends (gmail.com)
    {
        "from": "sarah.jenkins@gmail.com",
        "subject": "Coffee this weekend?",
        "category": "personal_friend",
        "reply_likely": True
    },
    {
        "from": "mike.chen@gmail.com",
        "subject": "Dude check out this meme",
        "category": "personal_friend",
        "reply_likely": False
    },
    {
        "from": "emma.rodriguez@gmail.com",
        "subject": "Want to grab dinner Thursday?",
        "category": "personal_friend",
        "reply_likely": True
    },
    {
        "from": "alex.park@outlook.com",
        "subject": "Happy birthday!! 🎂",
        "category": "personal_friend",
        "reply_likely": True
    },
    {
        "from": "jessica.liu@yahoo.com",
        "subject": "Movie night Friday?",
        "category": "personal_friend",
        "reply_likely": True
    },
    
    # Personal family
    {
        "from": "mom.smith@gmail.com",
        "subject": "Did you eat today?",
        "category": "personal_family",
        "reply_likely": True
    },
    {
        "from": "dad.johnson@yahoo.com",
        "subject": "Coming home for Thanksgiving?",
        "category": "personal_family",
        "reply_likely": True
    },
    {
        "from": "sister.kate@gmail.com",
        "subject": "Can you help me with something?",
        "category": "personal_family",
        "reply_likely": True
    },
    
    # Teachers/Professors (.edu)
    {
        "from": "prof.anderson@stanford.edu",
        "subject": "Office hours this week",
        "category": "teacher_professor",
        "reply_likely": False
    },
    {
        "from": "jsmith@berkeley.edu",
        "subject": "Assignment 3 extension request",
        "category": "teacher_professor",
        "reply_likely": True
    },
    {
        "from": "dr.wilson@mit.edu",
        "subject": "Research opportunity available",
        "category": "teacher_professor",
        "reply_likely": True
    },
    {
        "from": "teaching_assistant@yale.edu",
        "subject": "Your midterm grade is posted",
        "category": "teacher_professor",
        "reply_likely": False
    },
    
    # Newsletters
    {
        "from": "newsletter@morningbrew.com",
        "subject": "☕ Your daily dose of business news",
        "category": "newsletter",
        "reply_likely": False
    },
    {
        "from": "updates@techcrunch.com",
        "subject": "Top tech stories this week",
        "category": "newsletter",
        "reply_likely": False
    },
    {
        "from": "digest@theatlantic.com",
        "subject": "The Atlantic Daily: January 31",
        "category": "newsletter",
        "reply_likely": False
    },
    {
        "from": "newsletter@axios.com",
        "subject": "Axios AM: What you need to know",
        "category": "newsletter",
        "reply_likely": False
    },
    {
        "from": "subscribe@wired.com",
        "subject": "This Week in Tech",
        "category": "newsletter",
        "reply_likely": False
    },
    {
        "from": "updates@medium.com",
        "subject": "Recommended reads for you",
        "category": "newsletter",
        "reply_likely": False
    },
    
    # Marketing/Sales
    {
        "from": "sales@hubspot.com",
        "subject": "Grow your business with HubSpot",
        "category": "marketing",
        "reply_likely": False
    },
    {
        "from": "offers@amazon.com",
        "subject": "Deals just for you - 50% off",
        "category": "marketing",
        "reply_likely": False
    },
    {
        "from": "promo@spotify.com",
        "subject": "Get 3 months of Premium for free",
        "category": "marketing",
        "reply_likely": False
    },
    {
        "from": "marketing@shopify.com",
        "subject": "Start your online store today",
        "category": "marketing",
        "reply_likely": False
    },
    
    # Work colleagues
    {
        "from": "john.doe@company.com",
        "subject": "Quick sync on Q1 roadmap",
        "category": "work_colleague",
        "reply_likely": True
    },
    {
        "from": "sarah.manager@company.com",
        "subject": "1:1 meeting tomorrow at 2pm",
        "category": "work_colleague",
        "reply_likely": True
    },
    {
        "from": "team@startup.io",
        "subject": "Sprint planning this Friday",
        "category": "work_colleague",
        "reply_likely": True
    },
    
    # Work external
    {
        "from": "contact@client-company.com",
        "subject": "Project proposal for review",
        "category": "work_external",
        "reply_likely": True
    },
    {
        "from": "partnerships@bigcorp.com",
        "subject": "Collaboration opportunity",
        "category": "work_external",
        "reply_likely": True
    },
    
    # Transactional
    {
        "from": "receipts@uber.com",
        "subject": "Your trip receipt",
        "category": "transactional",
        "reply_likely": False
    },
    {
        "from": "no-reply@doordash.com",
        "subject": "Your order has been delivered",
        "category": "transactional",
        "reply_likely": False
    },
    {
        "from": "noreply@netflix.com",
        "subject": "Your monthly bill is ready",
        "category": "transactional",
        "reply_likely": False
    },
    {
        "from": "receipts@apple.com",
        "subject": "Your receipt from Apple",
        "category": "transactional",
        "reply_likely": False
    },
    
    # Educational services (.edu)
    {
        "from": "housing@university.edu",
        "subject": "Dorm assignments for next semester",
        "category": "educational",
        "reply_likely": False
    },
    {
        "from": "library@college.edu",
        "subject": "Book due date reminder",
        "category": "educational",
        "reply_likely": False
    },
    {
        "from": "registrar@school.edu",
        "subject": "Course registration opens Monday",
        "category": "educational",
        "reply_likely": False
    },
    {
        "from": "dining@campus.edu",
        "subject": "New dining hall hours",
        "category": "educational",
        "reply_likely": False
    },
    
    # Tech community
    {
        "from": "events@ycombinator.com",
        "subject": "YC Startup School is back",
        "category": "tech_community",
        "reply_likely": False
    },
    {
        "from": "hello@mlh.io",
        "subject": "Upcoming hackathons near you",
        "category": "tech_community",
        "reply_likely": False
    },
    {
        "from": "community@devpost.com",
        "subject": "Join our global hackathon",
        "category": "tech_community",
        "reply_likely": False
    },
    
    # Event platforms
    {
        "from": "events@lu.ma",
        "subject": "Tech mixer this Thursday",
        "category": "event_platform",
        "reply_likely": False
    },
    {
        "from": "tickets@eventbrite.com",
        "subject": "Your ticket for AI Conference",
        "category": "event_platform",
        "reply_likely": False
    },
    {
        "from": "rsvp@meetup.com",
        "subject": "Python Developers Meetup tomorrow",
        "category": "event_platform",
        "reply_likely": False
    },
    
    # Career platforms
    {
        "from": "jobs@linkedin.com",
        "subject": "5 new jobs match your profile",
        "category": "career_platform",
        "reply_likely": False
    },
    {
        "from": "opportunities@handshake.com",
        "subject": "Software Engineer intern at Google",
        "category": "career_platform",
        "reply_likely": False
    },
    {
        "from": "alerts@indeed.com",
        "subject": "New job alert: Full Stack Developer",
        "category": "career_platform",
        "reply_likely": False
    },
]


def generate_behavior_signals(category: str, reply_likely: bool) -> Dict:
    """Generate realistic behavior signals for an email."""
    
    # Base probabilities by category
    if category in ["personal_friend", "personal_family", "teacher_professor"]:
        star_prob = 0.3
        read_prob = 0.9
        important_prob = 0.4
    elif category in ["newsletter", "marketing"]:
        star_prob = 0.05
        read_prob = 0.4
        important_prob = 0.1
    elif category == "transactional":
        star_prob = 0.1
        read_prob = 0.7
        important_prob = 0.2
    elif category in ["work_colleague", "work_external"]:
        star_prob = 0.4
        read_prob = 0.95
        important_prob = 0.6
    else:
        star_prob = 0.15
        read_prob = 0.6
        important_prob = 0.2
    
    is_read = random.random() < read_prob
    is_starred = random.random() < star_prob
    is_important = random.random() < important_prob
    has_reply = reply_likely and random.random() < 0.5
    
    # Generate realistic days_unread
    if not is_read:
        days_unread = random.randint(1, 30)
    else:
        days_unread = random.randint(0, 3)
    
    return {
        "is_read": is_read,
        "is_starred": is_starred,
        "is_archived": random.random() < 0.3,
        "is_deleted": False,
        "is_important": is_important,
        "has_reply": has_reply,
        "days_unread": days_unread,
        "labels": ["INBOX"] if not is_starred else ["INBOX", "STARRED"]
    }


def generate_timestamp(days_ago: int) -> str:
    """Generate timestamp X days in the past."""
    dt = datetime.utcnow() - timedelta(days=days_ago)
    return dt.isoformat() + "Z"


@weave.op()
async def generate_synthetic_emails(count: int = 80):
    """Generate and store synthetic emails in Firebase."""
    
    print(f"🤖 Generating {count} synthetic emails...")
    
    # Duplicate templates to reach desired count
    emails_to_generate = []
    while len(emails_to_generate) < count:
        emails_to_generate.extend(SYNTHETIC_EMAILS)
    emails_to_generate = emails_to_generate[:count]
    
    # Generate each email with realistic data
    generated = 0
    for i, template in enumerate(emails_to_generate):
        # Random timestamp (last 60 days)
        days_ago = random.randint(1, 60)
        timestamp = generate_timestamp(days_ago)
        
        # Generate behavior signals
        behavior = generate_behavior_signals(
            template["category"],
            template["reply_likely"]
        )
        
        # Create email document
        email_doc = {
            "from": template["from"],
            "subject": template["subject"],
            "timestamp": timestamp,
            "thread_id": f"synthetic_thread_{i}",
            "snippet": f"Preview of {template['subject']}...",
            "source": "synthetic",
            **behavior
        }
        
        # Store in Firebase
        doc_ref = db.collection('emails').document()
        doc_ref.set(email_doc)
        generated += 1
        
        if generated % 20 == 0:
            print(f"  ✅ Generated {generated}/{count} emails...")
    
    print(f"\n✨ Complete! Generated {generated} synthetic emails")
    print(f"   Categories represented:")
    print(f"   - Personal friends/family")
    print(f"   - Teachers/professors") 
    print(f"   - Newsletters")
    print(f"   - Marketing")
    print(f"   - Work (colleagues + external)")
    print(f"   - Transactional")
    print(f"   - Educational services")
    print(f"   - Tech community")
    print(f"   - Event/career platforms")
    print(f"\n💡 Run bootstrap to analyze: python agent/run_bootstrap.py")


if __name__ == "__main__":
    weave.init('email-agent')
    asyncio.run(generate_synthetic_emails(count=80))
