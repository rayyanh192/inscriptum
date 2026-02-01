"""
Model Updater - Agent changes its OWN decision logic
This is where learned rules become EXECUTABLE CODE
"""

import weave
from datetime import datetime
from typing import Dict, List, Any
import json


@weave.op()
async def update_decision_model(db, new_rules: List[Dict], new_weights: Dict):
    """
    Agent REWRITES its own decision-making code.
    This is the CRITICAL difference vs pattern matching.
    
    After calling this, agent makes DIFFERENT decisions than before.
    """
    
    # Store new weights
    db.collection('model_config').document('current_weights').set({
        'weights': new_weights,
        'updated_at': datetime.utcnow().isoformat(),
        'version': await get_next_version(db)
    })
    
    # Activate new rules
    for rule in new_rules:
        db.collection('learned_rules').document(rule['id']).set({
            **rule,
            'status': 'active',
            'activated_at': datetime.utcnow().isoformat()
        })
    
    print(f"✅ Model updated: {len(new_rules)} new rules, weights adjusted")
    return {
        'new_rules_activated': len(new_rules),
        'weights_updated': new_weights,
        'version': await get_next_version(db)
    }


async def get_next_version(db) -> int:
    """Get next model version number."""
    current = db.collection('model_config').document('current_weights').get()
    if current.exists:
        return current.to_dict().get('version', 0) + 1
    return 1


@weave.op()
async def apply_learned_rules_to_decision(
    email: Dict, 
    person_context: Dict,
    cluster_context: Dict,
    base_prediction: Dict,
    db
) -> Dict:
    """
    CRITICAL: This is where learned rules override base prediction.
    
    Agent checks if it has learned a BETTER strategy for this email.
    If yes, uses learned strategy instead of base prediction.
    """
    
    # Get all active learned rules
    rules = []
    for doc in db.collection('learned_rules').where('status', '==', 'active').stream():
        rules.append(doc.to_dict())
    
    # Sort by confidence (use most confident rules first)
    rules.sort(key=lambda r: r.get('confidence', 0), reverse=True)
    
    # Check each rule to see if it applies
    for rule in rules:
        if rule_matches(rule, email, person_context, cluster_context):
            # RULE APPLIES - Override base prediction
            print(f"🧠 Applying learned rule: {rule['pattern']}")
            
            # Record that we used this learned rule
            db.collection('rule_applications').add({
                'rule_id': rule['id'],
                'email_id': email.get('message_id'),
                'timestamp': datetime.utcnow().isoformat(),
                'overrode_base_prediction': base_prediction['action'],
                'used_learned_action': rule['action']
            })
            
            return {
                'action': rule['action'],
                'confidence': rule['confidence'],
                'reasoning': f"Learned rule: {rule['pattern']}",
                'learned_rule_id': rule['id'],
                'base_prediction': base_prediction  # Keep for comparison
            }
    
    # No learned rules apply - use base prediction
    return base_prediction


def rule_matches(rule: Dict, email: Dict, person_context: Dict, cluster_context: Dict) -> bool:
    """
    Check if a learned rule's conditions match this email.
    
    THIS IS EXECUTABLE PATTERN MATCHING.
    Rules discovered through exploration become REAL CONDITIONS.
    """
    
    conditions = rule.get('conditions', {})
    
    # Check each condition
    for key, expected_value in conditions.items():
        if key == 'sender_domain':
            actual_value = email.get('from', '').split('@')[-1]
            if actual_value != expected_value:
                return False
        
        elif key == 'relationship_type':
            actual_value = person_context.get('relationship', {}).get('relationship_type')
            if actual_value != expected_value:
                return False
        
        elif key == 'hour_of_day':
            # Check time window
            email_hour = datetime.fromisoformat(email['timestamp']).hour
            if 'min' in expected_value and email_hour < expected_value['min']:
                return False
            if 'max' in expected_value and email_hour > expected_value['max']:
                return False
        
        elif key == 'subject_contains':
            subject = email.get('subject', '').lower()
            if expected_value.lower() not in subject:
                return False
        
        elif key == 'importance_score':
            # Check threshold
            if 'min' in expected_value:
                actual_value = person_context.get('importance_score', 0)
                if actual_value < expected_value['min']:
                    return False
        
        elif key == 'cluster_reply_rate':
            if 'min' in expected_value:
                actual_value = cluster_context.get('avg_reply_rate', 0)
                if actual_value < expected_value['min']:
                    return False
        
        elif key == 'has_attachment':
            if email.get('has_attachment') != expected_value:
                return False
    
    # All conditions matched
    return True


@weave.op()
async def get_current_weights(db) -> Dict:
    """Get current decision weights."""
    doc = db.collection('model_config').document('current_weights').get()
    if doc.exists:
        return doc.to_dict()['weights']
    
    # Default weights (will be optimized through learning)
    return {
        'person_importance': 0.3,
        'cluster_pattern': 0.2,
        'content_urgency': 0.25,
        'learned_patterns': 0.15,
        'domain_signal': 0.1
    }


@weave.op()
async def deprecate_failing_rule(db, rule_id: str, reason: str):
    """
    Mark a learned rule as ineffective.
    
    CRITICAL: Self-learning means FORGETTING what doesn't work.
    """
    
    db.collection('learned_rules').document(rule_id).update({
        'status': 'deprecated',
        'deprecated_at': datetime.utcnow().isoformat(),
        'deprecation_reason': reason
    })
    
    print(f"🗑️  Deprecated rule {rule_id}: {reason}")


@weave.op()
async def get_rule_performance(db, rule_id: str) -> Dict:
    """
    Measure how well a learned rule performs.
    Used to decide if rule should be kept or deprecated.
    """
    
    # Get all applications of this rule
    applications = []
    docs = db.collection('rule_applications')\
        .where('rule_id', '==', rule_id)\
        .stream()
    
    for doc in docs:
        applications.append(doc.to_dict())
    
    if not applications:
        return {'times_used': 0, 'accuracy': 0.0}
    
    # Check feedback for each application
    correct = 0
    for app in applications:
        # Look up feedback for this email
        feedback = db.collection('feedback')\
            .where('email_id', '==', app['email_id'])\
            .limit(1)\
            .stream()
        
        for fb in feedback:
            if fb.to_dict().get('correct') == True:
                correct += 1
    
    return {
        'times_used': len(applications),
        'correct': correct,
        'accuracy': correct / len(applications) if applications else 0.0
    }


@weave.op()
async def optimize_weights_from_feedback(db) -> Dict:
    """
    Analyze recent feedback to find better signal weights.
    
    This is gradient descent on decision weights.
    Agent tunes its own parameters.
    """
    
    # Get recent decisions with feedback
    decisions = []
    for doc in db.collection('agent_decisions').limit(100).stream():
        data = doc.to_dict()
        if 'feedback' in data:
            decisions.append(data)
    
    if len(decisions) < 20:
        print("⚠️  Not enough feedback data to optimize weights")
        return await get_current_weights(db)
    
    # For each weight configuration, calculate accuracy
    # (Simplified - real version would use proper optimization)
    best_weights = None
    best_accuracy = 0
    
    weight_ranges = {
        'person_importance': [0.2, 0.3, 0.4],
        'cluster_pattern': [0.1, 0.2, 0.3],
        'content_urgency': [0.15, 0.25, 0.35],
        'learned_patterns': [0.1, 0.15, 0.2],
        'domain_signal': [0.05, 0.1, 0.15]
    }
    
    # Grid search (simplified)
    for person_w in weight_ranges['person_importance']:
        for cluster_w in weight_ranges['cluster_pattern']:
            for content_w in weight_ranges['content_urgency']:
                for learned_w in weight_ranges['learned_patterns']:
                    domain_w = 1.0 - person_w - cluster_w - content_w - learned_w
                    
                    if domain_w < 0:
                        continue
                    
                    weights = {
                        'person_importance': person_w,
                        'cluster_pattern': cluster_w,
                        'content_urgency': content_w,
                        'learned_patterns': learned_w,
                        'domain_signal': domain_w
                    }
                    
                    # Simulate accuracy with these weights
                    accuracy = simulate_accuracy_with_weights(decisions, weights)
                    
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_weights = weights
    
    if best_weights:
        print(f"✅ Found better weights: {best_accuracy:.1%} accuracy")
        return best_weights
    
    return await get_current_weights(db)


def simulate_accuracy_with_weights(decisions: List[Dict], weights: Dict) -> float:
    """
    Simulate how accurate decisions would be with these weights.
    """
    correct = 0
    
    for decision in decisions:
        # Recalculate importance with new weights
        signals = decision.get('signals', {})
        
        new_importance = (
            signals.get('person_score', 0.5) * weights['person_importance'] +
            signals.get('cluster_score', 0.5) * weights['cluster_pattern'] +
            signals.get('content_score', 0.5) * weights['content_urgency'] +
            signals.get('pattern_score', 0.5) * weights['learned_patterns'] +
            signals.get('domain_score', 0.5) * weights['domain_signal']
        )
        
        # Check if this would have been correct
        actual_action = decision.get('feedback', {}).get('correct_action')
        predicted_action = 'star' if new_importance > 0.6 else 'archive'
        
        if predicted_action == actual_action:
            correct += 1
    
    return correct / len(decisions) if decisions else 0.0
