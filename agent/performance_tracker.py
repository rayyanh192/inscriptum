"""
Performance Tracker - PROOF that agent is learning
Measures concrete improvement over time
"""

import weave
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np


@weave.op()
async def track_performance_metrics(db) -> Dict:
    """
    Track concrete evidence of self-improvement.
    
    CRITICAL: These metrics must TREND UPWARD to prove learning.
    """
    
    # Get decisions from different time windows
    decisions_week_1 = await get_decisions_in_window(db, days_ago=0, days_window=7)
    decisions_week_2 = await get_decisions_in_window(db, days_ago=7, days_window=7)
    decisions_week_3 = await get_decisions_in_window(db, days_ago=14, days_window=7)
    
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        
        # METRIC 1: Decision Accuracy (MUST IMPROVE)
        'accuracy_week_1': calculate_accuracy(decisions_week_1),
        'accuracy_week_2': calculate_accuracy(decisions_week_2),
        'accuracy_week_3': calculate_accuracy(decisions_week_3),
        'accuracy_trend': 'improving' if is_improving([
            calculate_accuracy(decisions_week_3),
            calculate_accuracy(decisions_week_2),
            calculate_accuracy(decisions_week_1)
        ]) else 'stagnant',
        
        # METRIC 2: Confidence Growth
        'avg_confidence_week_1': avg_confidence(decisions_week_1),
        'avg_confidence_week_2': avg_confidence(decisions_week_2),
        'avg_confidence_week_3': avg_confidence(decisions_week_3),
        
        # METRIC 3: User Intervention Rate (MUST DECREASE)
        'asks_user_rate_week_1': calculate_ask_rate(decisions_week_1),
        'asks_user_rate_week_2': calculate_ask_rate(decisions_week_2),
        'asks_user_rate_week_3': calculate_ask_rate(decisions_week_3),
        
        # METRIC 4: Strategy Discovery
        'total_learned_rules': await count_learned_rules(db),
        'rules_created_this_week': await count_rules_created(db, days=7),
        'active_rules': await count_active_rules(db),
        'deprecated_rules': await count_deprecated_rules(db),
        
        # METRIC 5: Exploration Success Rate
        'successful_explorations': await count_successful_explorations(db, days=7),
        'failed_explorations': await count_failed_explorations(db, days=7),
        
        # METRIC 6: Pattern Coverage
        'total_patterns_discovered': await count_discovered_patterns(db),
    }
    
    # Calculate derived metrics
    total_exp = metrics['successful_explorations'] + metrics['failed_explorations']
    metrics['exploration_success_rate'] = (
        metrics['successful_explorations'] / total_exp if total_exp > 0 else 0.0
    )
    
    metrics['intervention_reduction'] = (
        metrics['asks_user_rate_week_3'] - metrics['asks_user_rate_week_1']
    )
    
    # Store in Firebase
    db.collection('performance_metrics').document(
        datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    ).set(metrics)
    
    return metrics


async def get_decisions_in_window(db, days_ago: int, days_window: int) -> List[Dict]:
    """Get decisions from a specific time window."""
    start = (datetime.utcnow() - timedelta(days=days_ago + days_window)).isoformat()
    end = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
    
    decisions = []
    docs = db.collection('agent_decisions')\
        .where('timestamp', '>=', start)\
        .where('timestamp', '<', end)\
        .stream()
    
    for doc in docs:
        decisions.append(doc.to_dict())
    
    return decisions


def calculate_accuracy(decisions: List[Dict]) -> float:
    """Accuracy = % of decisions user agreed with."""
    if not decisions:
        return 0.0
    
    correct = sum(1 for d in decisions if d.get('feedback', {}).get('correct') == True)
    return correct / len(decisions)


def avg_confidence(decisions: List[Dict]) -> float:
    """Average confidence of decisions."""
    if not decisions:
        return 0.0
    
    confidences = [d.get('decision', {}).get('confidence', 0.5) for d in decisions]
    return sum(confidences) / len(confidences)


def calculate_ask_rate(decisions: List[Dict]) -> float:
    """% of emails where agent had to ask user."""
    if not decisions:
        return 0.0
    
    asks = sum(1 for d in decisions if d.get('decision', {}).get('action') == 'ask')
    return asks / len(decisions)


def is_improving(values: List[float]) -> bool:
    """Check if values show upward trend."""
    if len(values) < 2:
        return False
    return values[-1] > values[0] + 0.05  # At least 5% improvement


async def count_learned_rules(db) -> int:
    """Count all learned rules ever created."""
    return len(list(db.collection('learned_rules').stream()))


async def count_rules_created(db, days=7) -> int:
    """Count rules created in time window."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return len(list(
        db.collection('learned_rules').where('created_at', '>=', cutoff).stream()
    ))


async def count_active_rules(db) -> int:
    """Count currently active rules."""
    return len(list(
        db.collection('learned_rules').where('status', '==', 'active').stream()
    ))


async def count_deprecated_rules(db) -> int:
    """Count deprecated rules."""
    return len(list(
        db.collection('learned_rules').where('status', '==', 'deprecated').stream()
    ))


async def count_successful_explorations(db, days=7) -> int:
    """Count validated exploration hypotheses."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return len(list(
        db.collection('exploration_hypotheses')
        .where('created_at', '>=', cutoff)
        .where('validation_result', '==', 'validated')
        .stream()
    ))


async def count_failed_explorations(db, days=7) -> int:
    """Count rejected exploration hypotheses."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return len(list(
        db.collection('exploration_hypotheses')
        .where('created_at', '>=', cutoff)
        .where('validation_result', '==', 'rejected')
        .stream()
    ))


async def count_discovered_patterns(db) -> int:
    """Count total patterns discovered through learning."""
    return len(list(db.collection('learned_rules').stream()))


@weave.op()
async def generate_improvement_report(db) -> str:
    """
    Human-readable report showing self-improvement.
    THIS IS WHAT YOU SHOW IN THE DEMO.
    """
    
    metrics = await track_performance_metrics(db)
    
    report = f"""
═══════════════════════════════════════════════════════════════
SELF-LEARNING AGENT: IMPROVEMENT REPORT
═══════════════════════════════════════════════════════════════

📈 ACCURACY IMPROVEMENT:
   Week 3: {metrics['accuracy_week_3']:.1%}
   Week 2: {metrics['accuracy_week_2']:.1%}
   Week 1: {metrics['accuracy_week_1']:.1%}
   Trend: {metrics['accuracy_trend'].upper()}
   
   {f"✅ +{(metrics['accuracy_week_1'] - metrics['accuracy_week_3']) * 100:.1f}% improvement" if metrics['accuracy_trend'] == 'improving' else '⚠️  No improvement detected'}

🤔 CONFIDENCE GROWTH:
   Week 3: {metrics['avg_confidence_week_3']:.1%}
   Week 1: {metrics['avg_confidence_week_1']:.1%}
   {f"✅ Agent is {(metrics['avg_confidence_week_1'] - metrics['avg_confidence_week_3']) * 100:.1f}% more confident" if metrics['avg_confidence_week_1'] > metrics['avg_confidence_week_3'] else ''}

🙋 USER INTERVENTION:
   Week 3: Asked user {metrics['asks_user_rate_week_3']:.1%} of time
   Week 1: Asked user {metrics['asks_user_rate_week_1']:.1%} of time
   Reduction: {abs(metrics['intervention_reduction']):.1%}
   {f"✅ {abs(metrics['intervention_reduction']) * 100:.0f}% fewer interruptions" if metrics['intervention_reduction'] < 0 else ''}

🧠 STRATEGY DISCOVERY:
   Total Rules Learned: {metrics['total_learned_rules']}
   New Rules This Week: {metrics['rules_created_this_week']}
   Active Rules: {metrics['active_rules']}
   Deprecated (ineffective): {metrics['deprecated_rules']}
   
   ✅ Agent discovered {metrics['total_learned_rules']} decision rules YOU NEVER CODED

🎯 EXPLORATION SUCCESS:
   Successful Experiments: {metrics['successful_explorations']}
   Failed Experiments: {metrics['failed_explorations']}
   Success Rate: {metrics['exploration_success_rate']:.1%}

═══════════════════════════════════════════════════════════════
CONCLUSION: Agent is {'✅ GENUINELY SELF-LEARNING' if metrics['accuracy_trend'] == 'improving' and metrics['total_learned_rules'] > 5 else '⚠️  NEEDS MORE DATA'}
═══════════════════════════════════════════════════════════════
"""
    
    return report
