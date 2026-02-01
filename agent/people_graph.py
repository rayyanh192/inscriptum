"""
People Graph Module - Relationship mapping and clustering
Maps email contacts and their relationships to the user
"""

import weave
from groq import Groq
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def get_cluster_context(relationship_type: str, db) -> Dict[str, Any]:
    """
    Get cluster-wide patterns for a relationship type.
    Shows how user typically responds to this type of person.
    
    Returns cluster statistics like:
    - Average reply rate for this cluster
    - Common response patterns
    - Typical actions taken
    """
    # Get cluster document (document ID IS the cluster name)
    cluster_doc = db.collection('relationship_clusters').document(relationship_type).get()
    
    if not cluster_doc.exists:
        return {
            "cluster_name": relationship_type,
            "size": 0,
            "patterns": "No cluster data available"
        }
    
    cluster_info = cluster_doc.to_dict()
    people_in_cluster = cluster_info.get('members', [])  # Changed from 'people' to 'members'
    
    if not people_in_cluster:
        return {
            "cluster_name": relationship_type,
            "size": cluster_info.get('size', 0),
            "patterns": f"Cluster has {cluster_info.get('size', 0)} people but no detailed data"
        }
    
    # Calculate cluster-wide metrics from members
    total_reply_rate = 0
    total_star_rate = 0
    total_delete_rate = 0
    count = 0
    
    for member in people_in_cluster[:20]:  # Sample max 20
        person_email = member.get('email')
        doc_id = person_email.replace('@', '_at_').replace('.', '_')
        person_doc = db.collection('people').document(doc_id).get()
        
        if person_doc.exists:
            person_data = person_doc.to_dict()
            metrics = person_data.get('behavior_metrics', {})
            
            total_reply_rate += metrics.get('reply_rate', 0)
            total_star_rate += metrics.get('starred_rate', 0)
            total_delete_rate += metrics.get('delete_rate', 0)
            count += 1
    
    if count == 0:
        return {
            "cluster_name": relationship_type,
            "size": len(people_in_cluster),
            "patterns": "Insufficient data"
        }
    
    # Calculate averages
    avg_reply_rate = total_reply_rate / count
    avg_star_rate = total_star_rate / count
    avg_delete_rate = total_delete_rate / count
    
    # Determine typical action
    if avg_reply_rate > 0.5:
        typical_action = "reply"
    elif avg_star_rate > 0.3:
        typical_action = "star"
    elif avg_delete_rate > 0.3:
        typical_action = "delete"
    else:
        typical_action = "archive"
    
    return {
        "cluster_name": relationship_type,
        "size": len(people_in_cluster),
        "avg_reply_rate": avg_reply_rate,
        "avg_star_rate": avg_star_rate,
        "avg_delete_rate": avg_delete_rate,
        "typical_action": typical_action,
        "avg_importance": cluster_info.get('avg_importance', 0.5),
        "patterns": f"You typically {typical_action} emails from {relationship_type} ({avg_reply_rate:.0%} reply rate)"
    }


@weave.op()
async def analyze_person(email_address: str, emails: List[Dict], db) -> Dict[str, Any]:
    """
    Analyze a person based on all email interactions.
    
    Args:
        email_address: The email address to analyze
        emails: List of emails involving this person
        db: Firestore client
    
    Returns:
        Complete person profile with relationship metrics
    """
    # Clean email address
    if '<' in email_address:
        email_address = email_address.split('<')[1].split('>')[0]
    email_address = email_address.lower().strip()
    
    # Check if profile already exists
    doc_id = email_address.replace('@', '_at_').replace('.', '_')
    existing = db.collection('people').document(doc_id).get()
    
    if existing.exists:
        profile = existing.to_dict()
        # Update with new data
        profile = await update_person_profile(profile, emails)
    else:
        # Create new profile
        profile = await create_person_profile(email_address, emails)
    
    # Store updated profile
    db.collection('people').document(doc_id).set(profile)
    
    return profile


@weave.op()
async def create_person_profile(email_address: str, emails: List[Dict]) -> Dict[str, Any]:
    """Create a new person profile from emails."""
    
    profile = {
        "email": email_address,
        "domain": email_address.split('@')[1] if '@' in email_address else "unknown",
        "name": extract_name_from_emails(emails),
        "total_interactions": len(emails),
        "first_contact": None,
        "last_contact": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Calculate interaction metrics
    profile["metrics"] = calculate_interaction_metrics(emails)
    
    # Infer relationship attributes
    profile["relationship"] = await infer_relationship_attributes(email_address, emails)
    
    # Calculate importance score
    profile["importance_score"] = calculate_person_importance(profile["metrics"])
    
    # Extract communication patterns
    profile["communication_patterns"] = extract_communication_patterns(emails)
    
    # Timestamps
    timestamps = []
    for email in emails:
        ts = email.get('internal_date') or email.get('timestamp')
        if ts:
            timestamps.append(ts)
    
    if timestamps:
        profile["first_contact"] = min(timestamps)
        profile["last_contact"] = max(timestamps)
    
    return profile


@weave.op()
async def update_person_profile(existing: Dict, new_emails: List[Dict]) -> Dict[str, Any]:
    """Update an existing person profile with new email data."""
    
    profile = existing.copy()
    profile["total_interactions"] = existing.get("total_interactions", 0) + len(new_emails)
    profile["updated_at"] = datetime.utcnow().isoformat()
    
    # Recalculate metrics
    all_metrics = calculate_interaction_metrics(new_emails)
    
    # Merge with existing metrics (weighted average)
    old_count = existing.get("total_interactions", 1)
    new_count = len(new_emails)
    total = old_count + new_count
    
    old_metrics = existing.get("metrics", {})
    merged_metrics = {}
    
    for key in set(list(all_metrics.keys()) + list(old_metrics.keys())):
        old_val = old_metrics.get(key, 0)
        new_val = all_metrics.get(key, 0)
        merged_metrics[key] = (old_val * old_count + new_val * new_count) / total
    
    profile["metrics"] = merged_metrics
    profile["importance_score"] = calculate_person_importance(merged_metrics)
    
    # Update last contact
    for email in new_emails:
        ts = email.get('internal_date') or email.get('timestamp')
        if ts:
            current_last = profile.get("last_contact")
            if not current_last or ts > current_last:
                profile["last_contact"] = ts
    
    return profile


def extract_name_from_emails(emails: List[Dict]) -> Optional[str]:
    """Extract the person's name from email headers."""
    for email in emails:
        from_field = email.get('from', '')
        if '<' in from_field:
            name = from_field.split('<')[0].strip()
            if name and name != '':
                # Remove quotes if present
                name = name.strip('"\'')
                return name
    return None


def calculate_interaction_metrics(emails: List[Dict]) -> Dict[str, float]:
    """Calculate detailed interaction metrics."""
    if not emails:
        return {}
    
    total = len(emails)
    metrics = {
        "total_count": total,
        "starred_rate": sum(1 for e in emails if e.get('is_starred', False)) / total,
        "reply_rate": sum(1 for e in emails if e.get('has_reply', False)) / total,
        "read_rate": sum(1 for e in emails if e.get('is_read', False)) / total,
        "archive_rate": sum(1 for e in emails if e.get('is_archived', False)) / total,
        "delete_rate": sum(1 for e in emails if e.get('is_deleted', False)) / total,
        "important_rate": sum(1 for e in emails if e.get('is_important', False)) / total,
    }
    
    # Calculate average response time (if data available)
    days_unread = [e.get('days_unread', 0) for e in emails if e.get('days_unread') is not None]
    if days_unread:
        metrics["avg_days_unread"] = sum(days_unread) / len(days_unread)
    
    return metrics


@weave.op()
async def infer_relationship_attributes(email_address: str, emails: List[Dict]) -> Dict[str, Any]:
    """Use LLM to infer relationship attributes."""
    
    # Gather context
    domain = email_address.split('@')[1] if '@' in email_address else ""
    subjects = [e.get('subject', '') for e in emails[:10]]
    snippets = [e.get('snippet', '')[:100] for e in emails[:5]]
    
    prompt = f"""Analyze this email contact and determine their relationship attributes.

Email: {email_address}
Domain: {domain}
Recent subjects: {subjects}
Content snippets: {snippets}

Respond in JSON format with these fields:
{{
    "type": "work|personal|commercial|automated|unknown",
    "category": "colleague|client|vendor|friend|family|newsletter|notification|marketing|other",
    "formality_level": "formal|semi-formal|informal",
    "expected_response_time": "immediate|same_day|few_days|no_response_needed",
    "priority_default": "high|medium|low"
}}

Respond with ONLY the JSON, no other text."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You analyze email relationships. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Error inferring relationship: {e}")
        return {
            "type": "unknown",
            "category": "other",
            "formality_level": "semi-formal",
            "expected_response_time": "few_days",
            "priority_default": "medium"
        }


def calculate_person_importance(metrics: Dict) -> float:
    """Calculate overall importance score for a person."""
    score = 0.5  # Baseline
    
    # Positive signals
    score += metrics.get('starred_rate', 0) * 0.25
    score += metrics.get('reply_rate', 0) * 0.2
    score += metrics.get('important_rate', 0) * 0.15
    score += min(metrics.get('total_count', 0) / 50, 0.1)  # More emails = slightly more important
    
    # Negative signals
    score -= metrics.get('delete_rate', 0) * 0.25
    score -= metrics.get('archive_rate', 0) * 0.05
    
    # Clamp to 0-1
    return max(0.0, min(1.0, score))


def extract_communication_patterns(emails: List[Dict]) -> Dict[str, Any]:
    """Extract communication patterns from emails."""
    patterns = {
        "typical_subject_keywords": [],
        "communication_frequency": "unknown",
        "thread_tendency": "unknown"
    }
    
    if not emails:
        return patterns
    
    # Analyze subjects for keywords
    all_subjects = ' '.join([e.get('subject', '') for e in emails]).lower()
    common_words = ['re:', 'fwd:', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
    words = all_subjects.split()
    word_freq = defaultdict(int)
    for word in words:
        if len(word) > 3 and word not in common_words:
            word_freq[word] += 1
    
    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    patterns["typical_subject_keywords"] = [k[0] for k in top_keywords]
    
    # Analyze frequency
    total = len(emails)
    if total >= 20:
        patterns["communication_frequency"] = "frequent"
    elif total >= 5:
        patterns["communication_frequency"] = "regular"
    else:
        patterns["communication_frequency"] = "occasional"
    
    # Thread tendency
    thread_ids = set(e.get('thread_id') for e in emails if e.get('thread_id'))
    if len(thread_ids) < total * 0.5:
        patterns["thread_tendency"] = "long_threads"
    else:
        patterns["thread_tendency"] = "single_emails"
    
    return patterns


@weave.op()
async def cluster_relationships(db) -> Dict[str, Any]:
    """
    Cluster people into relationship groups.
    Uses domain and behavior patterns for clustering.
    """
    print("\n" + "="*60)
    print("🔗 CLUSTERING RELATIONSHIPS")
    print("="*60)
    
    # Fetch all people profiles
    people = []
    docs = db.collection('people').stream()
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        people.append(data)
    
    if not people:
        return {"status": "no_data", "clusters": []}
    
    print(f"👥 Found {len(people)} people to cluster")
    
    # Cluster by relationship type
    clusters = defaultdict(list)
    
    for person in people:
        # Get relationship type from bootstrap
        rel_type = person.get('relationship', {}).get('type', 'other')
        
        # Use relationship type as cluster key directly
        cluster_key = rel_type
        clusters[cluster_key].append({
            "email": person.get('email'),
            "name": person.get('name'),
            "importance_score": person.get('importance_score', 0.5),
            "domain": person.get('domain', 'unknown')
        })
    
    # Convert to list and sort by size
    cluster_list = []
    for cluster_name, members in clusters.items():
        cluster_list.append({
            "name": cluster_name,
            "size": len(members),
            "members": members,
            "avg_importance": sum(m.get('importance_score', 0.5) for m in members) / len(members) if members else 0
        })
    
    cluster_list.sort(key=lambda x: x['size'], reverse=True)
    
    # Store clusters in Firebase
    for cluster in cluster_list:
        cluster_id = cluster['name'].replace(' ', '_').lower()
        cluster['updated_at'] = datetime.utcnow().isoformat()
        db.collection('relationship_clusters').document(cluster_id).set(cluster)
    
    print(f"✅ Created {len(cluster_list)} clusters")
    for c in cluster_list[:5]:
        print(f"   - {c['name']}: {c['size']} people (avg importance: {c['avg_importance']:.2f})")
    
    return {
        "status": "success",
        "total_clusters": len(cluster_list),
        "total_people": len(people),
        "clusters": cluster_list
    }


@weave.op()
async def get_person_context(email_address: str, db) -> Optional[Dict[str, Any]]:
    """
    Get context about a person for decision making.
    
    Args:
        email_address: The sender's email
        db: Firestore client
    
    Returns:
        Person context or None if not found
    """
    # Clean email address
    if '<' in email_address:
        email_address = email_address.split('<')[1].split('>')[0]
    email_address = email_address.lower().strip()
    
    doc_id = email_address.replace('@', '_at_').replace('.', '_')
    doc = db.collection('people').document(doc_id).get()
    
    if doc.exists:
        return doc.to_dict()
    return None


@weave.op()
async def update_person_after_action(email_address: str, action: str, db) -> None:
    """
    Update person profile after an action is taken.
    This helps the system learn from each interaction.
    """
    # Clean email
    if '<' in email_address:
        email_address = email_address.split('<')[1].split('>')[0]
    email_address = email_address.lower().strip()
    
    doc_id = email_address.replace('@', '_at_').replace('.', '_')
    doc_ref = db.collection('people').document(doc_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return
    
    profile = doc.to_dict()
    
    # Update action history
    action_history = profile.get('action_history', [])
    action_history.append({
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Keep only last 100 actions
    if len(action_history) > 100:
        action_history = action_history[-100:]
    
    profile['action_history'] = action_history
    profile['updated_at'] = datetime.utcnow().isoformat()
    
    # Update action counts
    action_counts = profile.get('action_counts', {})
    action_counts[action] = action_counts.get(action, 0) + 1
    profile['action_counts'] = action_counts
    
    doc_ref.set(profile)
