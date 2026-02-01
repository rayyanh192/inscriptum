"""
Bootstrap Module - Cold-start learning from Gmail history
Learns user patterns from existing email behavior
"""

import weave
from groq import Groq
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def bootstrap_from_gmail_history(db) -> Dict[str, Any]:
    """
    Cold-start learning from past Gmail behavior.
    Analyzes all emails in Firebase to build initial models.
    
    Args:
        db: Firestore client
    
    Returns:
        Dict with bootstrap results and statistics
    """
    print("\n" + "="*60)
    print("🚀 BOOTSTRAPPING FROM GMAIL HISTORY")
    print("="*60)
    
    # Step 1: Fetch all emails from Firebase
    emails = await fetch_all_emails(db)
    print(f"\n📧 Found {len(emails)} emails to analyze")
    
    if not emails:
        return {
            "status": "no_data",
            "message": "No emails found in Firebase",
            "people_created": 0,
            "patterns_learned": 0
        }
    
    # Step 2: Group emails by sender
    sender_groups = group_emails_by_sender(emails)
    print(f"👥 Found {len(sender_groups)} unique senders")
    
    # Step 3: Analyze each sender and create people profiles
    people_created = 0
    for sender_email, sender_emails in sender_groups.items():
        profile = await analyze_sender_for_bootstrap(sender_email, sender_emails)
        
        # Store in Firebase people/ collection
        doc_ref = db.collection('people').document(sender_email.replace('@', '_at_').replace('.', '_'))
        doc_ref.set(profile)
        people_created += 1
        print(f"  ✅ Created profile for: {sender_email[:30]}...")
    
    # Step 4: Extract importance patterns
    patterns = await extract_importance_patterns(emails)
    
    # Step 5: Store patterns in Firebase
    patterns_ref = db.collection('learned_patterns').document('importance')
    patterns_ref.set(patterns)
    
    print(f"\n✨ Bootstrap complete!")
    print(f"   - People profiles created: {people_created}")
    print(f"   - Patterns learned: {len(patterns.get('rules', []))}")
    
    return {
        "status": "success",
        "people_created": people_created,
        "patterns_learned": len(patterns.get('rules', [])),
        "total_emails_analyzed": len(emails),
        "timestamp": datetime.utcnow().isoformat()
    }


@weave.op()
async def fetch_all_emails(db) -> List[Dict[str, Any]]:
    """Fetch all emails from Firebase emails/ collection."""
    emails = []
    docs = db.collection('emails').stream()
    
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        emails.append(data)
    
    return emails


def group_emails_by_sender(emails: List[Dict]) -> Dict[str, List[Dict]]:
    """Group emails by sender email address."""
    groups = {}
    for email in emails:
        sender = email.get('from', 'unknown')
        # Extract email address from "Name <email@domain.com>" format
        if '<' in sender:
            sender = sender.split('<')[1].split('>')[0]
        sender = sender.lower().strip()
        
        if sender not in groups:
            groups[sender] = []
        groups[sender].append(email)
    
    return groups


@weave.op()
async def analyze_sender_for_bootstrap(sender_email: str, emails: List[Dict]) -> Dict[str, Any]:
    """
    Analyze a sender based on email history to build initial profile.
    
    Uses NO hardcoded field names - dynamically checks what exists.
    """
    profile = {
        "email": sender_email,
        "total_emails": len(emails),
        "first_seen": None,
        "last_seen": None,
        "created_at": datetime.utcnow().isoformat(),
        "source": "bootstrap"
    }
    
    # Extract domain
    if '@' in sender_email:
        profile["domain"] = sender_email.split('@')[1]
    
    # Analyze behavior signals (use .get() for all fields)
    starred_count = 0
    replied_count = 0
    read_count = 0
    archived_count = 0
    deleted_count = 0
    important_count = 0
    total_days_unread = 0
    unread_count = 0
    
    timestamps = []
    subjects = []
    
    for email in emails:
        # Behavior signals - check dynamically
        if email.get('is_starred', False):
            starred_count += 1
        if email.get('has_reply', False):
            replied_count += 1
        if email.get('is_read', False):
            read_count += 1
        if email.get('is_archived', False):
            archived_count += 1
        if email.get('is_deleted', False):
            deleted_count += 1
        if email.get('is_important', False):
            important_count += 1
        
        # Days unread tracking
        days_unread = email.get('days_unread')
        if days_unread is not None:
            total_days_unread += days_unread
            unread_count += 1
        
        # Timestamps - normalize to string format
        ts = email.get('internal_date') or email.get('timestamp')
        if ts:
            # Convert integer timestamps to ISO string
            if isinstance(ts, int):
                from datetime import datetime as dt
                ts = dt.utcfromtimestamp(ts / 1000).isoformat() + "Z"
            timestamps.append(ts)
        
        # Subjects for analysis
        subject = email.get('subject', '')
        if subject:
            subjects.append(subject)
    
    # Calculate metrics
    total = len(emails)
    profile["behavior_metrics"] = {
        "starred_rate": starred_count / total if total > 0 else 0,
        "reply_rate": replied_count / total if total > 0 else 0,
        "read_rate": read_count / total if total > 0 else 0,
        "archive_rate": archived_count / total if total > 0 else 0,
        "delete_rate": deleted_count / total if total > 0 else 0,
        "important_rate": important_count / total if total > 0 else 0,
        "avg_days_unread": total_days_unread / unread_count if unread_count > 0 else None
    }
    
    # Calculate importance score from behavior
    importance_score = calculate_importance_from_behavior(profile["behavior_metrics"])
    profile["importance_score"] = importance_score
    
    # Determine relationship type via LLM
    relationship_type = await infer_relationship_type(sender_email, subjects, profile["domain"])
    
    # Store in nested relationship object to match people_graph expectations
    profile["relationship"] = {
        "type": relationship_type,
        "category": "inferred_from_bootstrap"
    }
    
    # Timestamps
    if timestamps:
        profile["first_seen"] = min(timestamps)
        profile["last_seen"] = max(timestamps)
    
    return profile


def calculate_importance_from_behavior(metrics: Dict) -> float:
    """
    Calculate importance score from behavior metrics.
    Higher score = more important sender.
    """
    score = 0.5  # Baseline
    
    # Positive signals
    score += metrics.get('starred_rate', 0) * 0.3  # Starred = very important
    score += metrics.get('reply_rate', 0) * 0.25   # Replied = engaged
    score += metrics.get('important_rate', 0) * 0.15  # Gmail flagged important
    
    # Negative signals
    score -= metrics.get('delete_rate', 0) * 0.3   # Deleted = not wanted
    score -= metrics.get('archive_rate', 0) * 0.1  # Archived = meh
    
    # Days unread penalty
    avg_unread = metrics.get('avg_days_unread')
    if avg_unread is not None and avg_unread > 7:
        score -= 0.1  # Long unread = low priority
    
    # Clamp to 0-1
    return max(0.0, min(1.0, score))


@weave.op()
async def infer_relationship_type(sender_email: str, subjects: List[str], domain: str) -> str:
    """Use strong heuristics + LLM to infer relationship type from sender info."""
    
    domain_lower = domain.lower() if domain else ""
    sender_lower = sender_email.lower()
    
    # STRONG heuristics first - these override LLM
    
    # 1. Automated/transactional senders
    if any(x in sender_lower for x in ['noreply', 'no-reply', 'donotreply', 'notifications']):
        if any(x in domain_lower for x in ['github', 'google', 'microsoft', 'apple']):
            return "transactional"
        return "automated"
    
    # 2. Educational
    if '.edu' in domain_lower:
        if any(x in sender_lower for x in ['housing', 'library', 'transportation', 'dining']):
            return "educational_services"
        return "educational"
    
    # 3. Newsletters/Marketing
    if any(x in domain_lower for x in ['beehiiv', 'substack', 'mailchimp', 'sendgrid', 'constantcontact']):
        return "newsletter"
    if any(x in sender_lower for x in ['news', 'newsletter', 'updates', 'digest']):
        return "newsletter"
    if any(x in domain_lower for x in ['nytimes', 'wsj', 'medium', 'substack']):
        return "newsletter"
    
    # 4. Job platforms
    if any(x in domain_lower for x in ['handshake', 'linkedin', 'indeed', 'glassdoor']):
        return "career_platform"
    
    # 5. Social/Community platforms
    if any(x in domain_lower for x in ['luma', 'eventbrite', 'meetup', 'extern']):
        return "event_platform"
    if any(x in domain_lower for x in ['ycombinator', 'mlh']):
        return "tech_community"
    
    # 6. Transactional services
    if any(x in domain_lower for x in ['transactcampus', 'paypal', 'stripe', 'venmo']):
        return "transactional"
    if any(x in domain_lower for x in ['hunter.io', 'apollo.io']):
        return "sales_tool"
    
    # 7. Canvas/Learning platforms
    if 'instructure.com' in domain_lower:
        return "learning_platform"
    
    # 8. For generic personal domains (gmail, yahoo, etc.), analyze content with LLM
    # Don't return early - let LLM distinguish friends/family/teachers/colleagues
    is_generic_personal_domain = any(x in domain_lower for x in ['gmail.com', 'yahoo.com', 'hotmail.com', 'icloud.com', 'outlook.com'])
    
    # For everything else (or generic personal domains), use LLM with better context
    subject_sample = subjects[:5] if subjects else ["(no subjects)"]
    
    # Enhanced prompt for better personal relationship detection
    domain_context = "(generic personal domain)" if is_generic_personal_domain else f"(domain: {domain})"
    
    prompt = f"""Classify this email sender into ONE specific category based on their email subjects and patterns:

Categories:
- personal_friend: Personal friend (casual topics, social plans, catching up)
- personal_family: Family member (family matters, personal life)
- teacher_professor: Teacher or professor (coursework, grades, academic advice)
- work_colleague: Colleague from same organization (work projects, meetings)
- work_external: Business contact, client, vendor (business deals, partnerships)
- newsletter: Newsletters, blogs, media subscriptions
- marketing: Promotional emails, sales outreach
- transactional: Receipts, confirmations, automated notifications
- educational: School/university communications (not from personal teachers)
- tech_community: Tech events, communities, hackathons
- other: Everything else

Sender: {sender_email} {domain_context}
Email subjects: {subject_sample}

Analyze the subjects to infer the relationship. Look for:
- Academic keywords (homework, class, assignment) → teacher_professor
- Casual/social keywords (hang out, dinner, weekend) → personal_friend
- Family keywords (mom, dad, family, home) → personal_family
- Work keywords (meeting, project, deadline) → work_colleague

Respond with ONLY the category name."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )
        category = response.choices[0].message.content.strip().lower().replace('-', '_')
        return category
    except Exception as e:
        print(f"  ⚠️ LLM error for {sender_email}: {e}")
        return "other"


@weave.op()
async def extract_importance_patterns(emails: List[Dict]) -> Dict[str, Any]:
    """
    Extract importance patterns from email behavior.
    Learn what makes an email important to this user.
    """
    patterns = {
        "rules": [],
        "statistics": {},
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Analyze starred emails
    starred_emails = [e for e in emails if e.get('is_starred', False)]
    if starred_emails:
        starred_domains = [e.get('from', '').split('@')[-1].split('>')[0] for e in starred_emails]
        domain_counts = {}
        for d in starred_domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1
        
        top_starred_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        patterns["rules"].append({
            "type": "starred_domain_pattern",
            "domains": [d[0] for d in top_starred_domains],
            "description": "Emails from these domains are often starred"
        })
    
    # Analyze deleted emails
    deleted_emails = [e for e in emails if e.get('is_deleted', False)]
    if deleted_emails:
        deleted_domains = [e.get('from', '').split('@')[-1].split('>')[0] for e in deleted_emails]
        domain_counts = {}
        for d in deleted_domains:
            domain_counts[d] = domain_counts.get(d, 0) + 1
        
        top_deleted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        patterns["rules"].append({
            "type": "deleted_domain_pattern",
            "domains": [d[0] for d in top_deleted_domains],
            "description": "Emails from these domains are often deleted"
        })
    
    # Analyze replied emails
    replied_emails = [e for e in emails if e.get('has_reply', False)]
    if replied_emails:
        patterns["rules"].append({
            "type": "reply_pattern",
            "count": len(replied_emails),
            "rate": len(replied_emails) / len(emails) if emails else 0,
            "description": f"User replies to {len(replied_emails)}/{len(emails)} emails"
        })
    
    # Statistics
    patterns["statistics"] = {
        "total_emails": len(emails),
        "starred_count": len(starred_emails),
        "deleted_count": len(deleted_emails),
        "replied_count": len(replied_emails),
        "starred_rate": len(starred_emails) / len(emails) if emails else 0,
        "delete_rate": len(deleted_emails) / len(emails) if emails else 0,
        "reply_rate": len(replied_emails) / len(emails) if emails else 0
    }
    
    return patterns


# CLI for running bootstrap
if __name__ == "__main__":
    import asyncio
    from . import db
    
    asyncio.run(bootstrap_from_gmail_history(db))
