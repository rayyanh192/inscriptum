"""
Strategy Evolution - Agent DISCOVERS new rules and DISCARDS failing ones
This is where the agent CHANGES ITS OWN BEHAVIOR.
"""

import weave
from groq import Groq
import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def evolve_strategies(db) -> Dict[str, Any]:
    """
    CRITICAL: Agent modifies its own decision-making logic.
    
    1. Analyzes which exploration strategies worked/failed
    2. Extracts patterns from successful explorations
    3. Creates NEW decision rules
    4. Deprecates failing strategies
    5. Optimizes decision weights
    """
    
    print("\n🧬 STRATEGY EVOLUTION STARTED")
    
    # STEP 1: Get exploration results
    validated_hypotheses = await get_validated_hypotheses(db, days=7)
    failed_hypotheses = await get_failed_hypotheses(db, days=7)
    
    print(f"   📊 Analyzed {len(validated_hypotheses)} successful + {len(failed_hypotheses)} failed explorations")
    
    # STEP 2: Extract generalizable patterns from successes
    new_strategies = await extract_generalizable_patterns(validated_hypotheses, db)
    
    print(f"   🔍 Discovered {len(new_strategies)} new generalizable patterns")
    
    # STEP 3: Create new decision rules
    new_rules = []
    for strategy in new_strategies:
        rule = await create_decision_rule(strategy, db)
        new_rules.append(rule)
        print(f"   ✅ Created rule: {rule['description']}")
    
    # STEP 4: Identify and deprecate failing strategies
    failing_rules = await identify_failing_strategies(db)
    deprecated_count = 0
    
    for failing_rule in failing_rules:
        if failing_rule['attempts'] > 20 and failing_rule['accuracy'] < 0.5:
            await deprecate_strategy(failing_rule['rule_id'], db)
            deprecated_count += 1
            print(f"   ❌ Deprecated: {failing_rule['description']}")
    
    # STEP 5: Optimize decision weights
    weight_optimization = await optimize_decision_weights(db)
    
    if weight_optimization.get('improved'):
        print(f"   ⚖️  Optimized weights: {weight_optimization['improvement']:.1%} improvement")
    
    print("🧬 STRATEGY EVOLUTION COMPLETE\n")
    
    return {
        'new_rules_created': len(new_rules),
        'rules_deprecated': deprecated_count,
        'weight_optimization': weight_optimization,
        'new_rules': new_rules
    }


async def get_validated_hypotheses(db, days=7) -> List[Dict]:
    """Get exploration hypotheses that user feedback confirmed."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    validated = []
    docs = db.collection('exploration_hypotheses')\
        .where('created_at', '>=', cutoff)\
        .where('validation_result', '==', 'validated')\
        .stream()
    
    for doc in docs:
        validated.append(doc.to_dict())
    
    return validated


async def get_failed_hypotheses(db, days=7) -> List[Dict]:
    """Get exploration hypotheses that failed."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    failed = []
    docs = db.collection('exploration_hypotheses')\
        .where('created_at', '>=', cutoff)\
        .where('validation_result', '==', 'rejected')\
        .stream()
    
    for doc in docs:
        failed.append(doc.to_dict())
    
    return failed


@weave.op()
async def extract_generalizable_patterns(validated_hypotheses: List[Dict], db) -> List[Dict]:
    """
    THE AGENT DISCOVERS PATTERNS YOU NEVER CODED.
    
    Example: "Emails from .edu sent before 9am get replied to 95% of time"
    This was NEVER programmed. The agent LEARNED it.
    """
    
    if len(validated_hypotheses) < 3:
        return []  # Need multiple validations
    
    # Group similar hypotheses
    clusters = cluster_similar_hypotheses(validated_hypotheses)
    
    patterns = []
    for cluster in clusters:
        if len(cluster) >= 3:  # Need multiple confirmations
            pattern = await synthesize_pattern_from_cluster(cluster, db)
            patterns.append(pattern)
    
    return patterns


def cluster_similar_hypotheses(hypotheses: List[Dict]) -> List[List[Dict]]:
    """Group hypotheses that test similar things."""
    clusters = defaultdict(list)
    
    for hyp in hypotheses:
        # Simple clustering by relationship type + action
        key = (
            hyp.get('email_context', {}).get('relationship_type', 'unknown'),
            hyp.get('alternative_action')
        )
        clusters[key].append(hyp)
    
    return [cluster for cluster in clusters.values() if len(cluster) >= 3]


@weave.op()
async def synthesize_pattern_from_cluster(cluster: List[Dict], db) -> Dict:
    """Use LLM to find common pattern across successful explorations."""
    
    examples = "\n".join([
        f"- Context: {h['email_context']}, Action: {h['alternative_action']}, Result: success"
        for h in cluster[:10]
    ])
    
    prompt = f"""Analyze successful email decisions and extract the generalizable pattern:

{examples}

What's the underlying rule that explains why these all succeeded?

Return JSON:
{{
    "condition": "Logical expression (e.g., 'relationship_type == personal_friend AND time_hour < 10')",
    "action": "what to do when condition is met",
    "confidence": 0-1 based on consistency,
    "description": "Plain English explanation"
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        pattern = json.loads(response.choices[0].message.content)
        pattern['source_count'] = len(cluster)
        pattern['source_hypotheses'] = [h.get('hypothesis') for h in cluster[:5]]
        
        return pattern
        
    except Exception as e:
        print(f"   ⚠️  Error synthesizing pattern: {e}")
        return None


@weave.op()
async def create_decision_rule(pattern: Dict, db) -> Dict:
    """
    Convert discovered pattern into EXECUTABLE decision logic.
    This becomes part of the agent's decision-making code.
    """
    
    rule = {
        'rule_id': f"learned_{datetime.utcnow().timestamp()}",
        'condition': pattern['condition'],
        'action': pattern['action'],
        'confidence': pattern['confidence'],
        'description': pattern['description'],
        'created_at': datetime.utcnow().isoformat(),
        'source': 'exploration_learning',
        'source_count': pattern['source_count'],
        'performance': {
            'accuracy': pattern['confidence'],
            'attempts': 0,
            'successes': 0,
            'failures': 0
        },
        'status': 'active'
    }
    
    # Store in learned_rules collection
    db.collection('learned_rules').document(rule['rule_id']).set(rule)
    
    return rule


async def identify_failing_strategies(db) -> List[Dict]:
    """Find decision rules that aren't working."""
    failing = []
    
    docs = db.collection('learned_rules').where('status', '==', 'active').stream()
    
    for doc in docs:
        rule = doc.to_dict()
        perf = rule.get('performance', {})
        
        attempts = perf.get('attempts', 0)
        successes = perf.get('successes', 0)
        
        if attempts > 10:
            accuracy = successes / attempts if attempts > 0 else 0
            
            if accuracy < 0.5:
                failing.append({
                    'rule_id': rule['rule_id'],
                    'description': rule['description'],
                    'accuracy': accuracy,
                    'attempts': attempts
                })
    
    return failing


async def deprecate_strategy(rule_id: str, db):
    """Mark a failing rule as deprecated."""
    rule_ref = db.collection('learned_rules').document(rule_id)
    rule_ref.update({
        'status': 'deprecated',
        'deprecated_at': datetime.utcnow().isoformat()
    })


@weave.op()
async def optimize_decision_weights(db) -> Dict:
    """
    Adjust signal weights based on what predicts outcomes best.
    
    THE AGENT TUNES ITSELF.
    """
    
    # Get recent decisions with feedback
    recent_decisions = await get_decisions_with_feedback(db, limit=100)
    
    if len(recent_decisions) < 20:
        return {'improved': False, 'reason': 'insufficient_data'}
    
    # Current weights
    current_weights = {
        'person_score': 0.35,
        'cluster_score': 0.20,
        'patterns_score': 0.20,
        'content_score': 0.20,
        'recency_score': 0.05
    }
    
    # Try different weight combinations
    best_accuracy = calculate_weight_accuracy(recent_decisions, current_weights)
    best_weights = current_weights.copy()
    
    # Simple grid search
    for person_w in [0.2, 0.3, 0.4, 0.5]:
        for cluster_w in [0.1, 0.2, 0.3]:
            for pattern_w in [0.1, 0.2, 0.3]:
                remaining = 1.0 - person_w - cluster_w - pattern_w
                if remaining < 0.1:
                    continue
                
                test_weights = {
                    'person_score': person_w,
                    'cluster_score': cluster_w,
                    'patterns_score': pattern_w,
                    'content_score': remaining * 0.8,
                    'recency_score': remaining * 0.2
                }
                
                accuracy = calculate_weight_accuracy(recent_decisions, test_weights)
                
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_weights = test_weights
    
    improvement = best_accuracy - calculate_weight_accuracy(recent_decisions, current_weights)
    
    if improvement > 0.02:  # At least 2% improvement
        # Store optimized weights
        db.collection('agent_config').document('decision_weights').set({
            'weights': best_weights,
            'updated_at': datetime.utcnow().isoformat(),
            'accuracy': best_accuracy
        })
        
        return {
            'improved': True,
            'old_weights': current_weights,
            'new_weights': best_weights,
            'improvement': improvement
        }
    
    return {'improved': False, 'reason': 'no_improvement_found'}


async def get_decisions_with_feedback(db, limit=100) -> List[Dict]:
    """Get recent decisions that have user feedback."""
    decisions = []
    
    docs = db.collection('agent_decisions')\
        .order_by('timestamp', direction='DESCENDING')\
        .limit(limit)\
        .stream()
    
    for doc in docs:
        data = doc.to_dict()
        if 'feedback' in data:
            decisions.append(data)
    
    return decisions


def calculate_weight_accuracy(decisions: List[Dict], weights: Dict) -> float:
    """Simulate what accuracy would be with these weights."""
    # Simplified - would need actual signal scores from decisions
    # For now, return baseline
    correct = sum(1 for d in decisions if d.get('feedback', {}).get('correct'))
    return correct / len(decisions) if decisions else 0.0
