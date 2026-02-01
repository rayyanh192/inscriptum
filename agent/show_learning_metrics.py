"""
Show concrete metrics proving self-learning.
No need to dig through Weave - just numbers.
"""

import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('agent/.env')

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from collections import defaultdict

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()


def get_learning_metrics():
    """Show measurable proof of self-learning."""
    
    print("\n" + "="*60)
    print("📊 SELF-LEARNING METRICS")
    print("="*60 + "\n")
    
    # 1. Patterns learned over time
    print("1️⃣  PATTERNS LEARNED:")
    print("-" * 60)
    patterns_doc = db.collection('learned_patterns').document('importance').get()
    if patterns_doc.exists:
        patterns = patterns_doc.to_dict().get('rules', [])
        print(f"   Total patterns: {len(patterns)}")
        
        if patterns:
            print(f"\n   Recent patterns:")
            for i, pattern in enumerate(patterns[-3:], 1):
                print(f"   {i}. {pattern.get('description', 'Pattern learned from feedback')}")
    else:
        print("   No patterns learned yet")
    
    # 2. People profiles (knowledge graph growth)
    print(f"\n2️⃣  PEOPLE KNOWLEDGE GRAPH:")
    print("-" * 60)
    people = list(db.collection('people').stream())
    print(f"   Total people profiled: {len(people)}")
    
    # Count by relationship type
    relationship_counts = defaultdict(int)
    for person in people:
        data = person.to_dict()
        rel_type = data.get('relationship', {}).get('type', 'unknown')
        relationship_counts[rel_type] += 1
    
    print(f"   Relationship types discovered:")
    for rel_type, count in sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     - {rel_type}: {count} people")
    
    # 3. Decision confidence over time
    print(f"\n3️⃣  DECISION CONFIDENCE TRENDS:")
    print("-" * 60)
    decisions = list(db.collection('agent_decisions').stream())
    
    if decisions:
        # Group by recency
        now = datetime.utcnow()
        recent_decisions = []
        older_decisions = []
        
        for dec in decisions:
            data = dec.to_dict()
            timestamp = data.get('timestamp')
            confidence = data.get('decision', {}).get('confidence', 0)
            
            if timestamp:
                # Parse timestamp
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', ''))
                    if (now - dt).total_seconds() < 3600:  # Last hour
                        recent_decisions.append(confidence)
                    else:
                        older_decisions.append(confidence)
        
        if recent_decisions:
            avg_recent = sum(recent_decisions) / len(recent_decisions)
            print(f"   Recent decisions (last hour): {len(recent_decisions)}")
            print(f"   Average confidence: {avg_recent:.2f}")
        
        if older_decisions:
            avg_older = sum(older_decisions) / len(older_decisions)
            print(f"\n   Older decisions: {len(older_decisions)}")
            print(f"   Average confidence: {avg_older:.2f}")
            
            if recent_decisions and older_decisions:
                improvement = avg_recent - avg_older
                print(f"\n   📈 Confidence improvement: {improvement:+.2f}")
                if improvement > 0:
                    print(f"   ✅ Agent is getting MORE confident over time!")
                elif improvement < 0:
                    print(f"   📉 Needs more training")
        
        print(f"\n   Total decisions made: {len(decisions)}")
    else:
        print("   No decisions made yet")
    
    # 4. Feedback applied
    print(f"\n4️⃣  FEEDBACK & CORRECTIONS:")
    print("-" * 60)
    feedback = list(db.collection('feedback').stream())
    print(f"   Total feedback received: {len(feedback)}")
    
    if feedback:
        feedback_types = defaultdict(int)
        for fb in feedback:
            data = fb.to_dict()
            fb_type = data.get('feedback_type', 'unknown')
            feedback_types[fb_type] += 1
        
        print(f"   Feedback breakdown:")
        for fb_type, count in feedback_types.items():
            print(f"     - {fb_type}: {count}")
    
    # 5. Clusters created
    print(f"\n5️⃣  RELATIONSHIP CLUSTERS:")
    print("-" * 60)
    clusters = list(db.collection('relationship_clusters').stream())
    if clusters:
        print(f"   Total clusters: {len(clusters)}")
        print(f"   Clusters identified:")
        for cluster in clusters[:5]:
            data = cluster.to_dict()
            print(f"     - {data.get('cluster_name')}: {data.get('size')} people (avg importance: {data.get('avg_importance', 0):.2f})")
    else:
        print("   No clusters created yet")
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 LEARNING SUMMARY")
    print("="*60)
    print(f"✅ Knowledge acquired:")
    print(f"   - {len(people)} people profiled")
    print(f"   - {len(patterns) if patterns_doc.exists else 0} patterns learned")
    print(f"   - {len(clusters)} relationship clusters")
    print(f"   - {len(decisions)} decisions made")
    print(f"   - {len(feedback)} feedback corrections applied")
    
    print(f"\n💡 To improve further:")
    print(f"   - Process more emails: python agent/train_with_feedback.py")
    print(f"   - Fetch new emails: node convo/fetch_once.js")
    print(f"   - Apply corrections to wrong decisions")
    print()


if __name__ == "__main__":
    get_learning_metrics()
