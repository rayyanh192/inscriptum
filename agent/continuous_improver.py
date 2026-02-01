"""
Continuous Improver - THE BACKGROUND LEARNING LOOP
This runs forever, constantly making the agent smarter
"""

import weave
import asyncio
from datetime import datetime, timedelta
from typing import Dict
import sys
import os

# Add agent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from strategy_evolution import evolve_strategies, optimize_decision_weights
from model_updater import update_decision_model, get_rule_performance, deprecate_failing_rule
from performance_tracker import track_performance_metrics, generate_improvement_report


@weave.op()
async def continuous_learning_loop(db, interval_hours: int = 6):
    """
    THE CORE SELF-LEARNING ENGINE.
    
    Runs in background forever:
    1. Analyze recent performance
    2. Evolve strategies (validate hypotheses, create new rules)
    3. Update model with learned rules
    4. Identify weak areas
    5. Optimize weights
    6. Deprecate failing rules
    7. Sleep and repeat
    
    CRITICAL: This is what makes it GENUINELY self-learning.
    """
    
    print("🚀 Starting continuous learning loop...")
    print(f"   Learning cycle every {interval_hours} hours")
    
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n{'='*70}")
        print(f"LEARNING CYCLE #{iteration} - {datetime.utcnow().isoformat()}")
        print(f"{'='*70}\n")
        
        try:
            # STEP 1: Analyze performance
            print("📊 Step 1: Analyzing performance...")
            metrics = await track_performance_metrics(db)
            print(f"   Accuracy: {metrics['accuracy_week_1']:.1%}")
            print(f"   Active rules: {metrics['active_rules']}")
            print(f"   Explorations success rate: {metrics['exploration_success_rate']:.1%}")
            
            # STEP 2: Evolve strategies
            print("\n🧬 Step 2: Evolving strategies...")
            evolution_results = await evolve_strategies(db)
            print(f"   Validated hypotheses: {evolution_results['validated_hypotheses']}")
            print(f"   New patterns discovered: {len(evolution_results['discovered_patterns'])}")
            print(f"   New rules created: {len(evolution_results['new_rules'])}")
            
            # STEP 3: Update model with new rules
            if evolution_results['new_rules']:
                print("\n🔄 Step 3: Updating decision model...")
                current_weights = await get_current_weights_safe(db)
                await update_decision_model(db, evolution_results['new_rules'], current_weights)
            else:
                print("\n🔄 Step 3: No new rules to activate")
            
            # STEP 4: Identify weak areas
            print("\n🔍 Step 4: Identifying weak areas...")
            weak_areas = await identify_weak_areas(db, metrics)
            if weak_areas:
                print(f"   Found {len(weak_areas)} areas needing improvement:")
                for area in weak_areas:
                    print(f"   - {area}")
            else:
                print("   ✅ No weak areas detected")
            
            # STEP 5: Optimize weights
            if metrics['accuracy_week_1'] < 0.8:  # Only optimize if not already good
                print("\n⚙️  Step 5: Optimizing decision weights...")
                new_weights = await optimize_decision_weights(db)
                await update_decision_model(db, [], new_weights)
                print(f"   Updated weights: {new_weights}")
            else:
                print("\n⚙️  Step 5: Weights already optimal")
            
            # STEP 6: Deprecate failing rules
            print("\n🗑️  Step 6: Deprecating failing rules...")
            deprecated_count = await deprecate_underperforming_rules(db)
            print(f"   Deprecated {deprecated_count} failing rules")
            
            # STEP 7: Generate improvement report
            print("\n📈 Step 7: Generating improvement report...")
            report = await generate_improvement_report(db)
            
            # Store report
            db.collection('learning_cycles').add({
                'iteration': iteration,
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': metrics,
                'evolution_results': evolution_results,
                'weak_areas': weak_areas,
                'report': report
            })
            
            print("\n" + report)
            
            # STEP 8: Sleep until next cycle
            print(f"\n💤 Sleeping for {interval_hours} hours until next learning cycle...")
            await asyncio.sleep(interval_hours * 3600)
        
        except Exception as e:
            print(f"❌ Error in learning cycle: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Sleep before retrying
            await asyncio.sleep(600)  # 10 minutes


async def get_current_weights_safe(db) -> Dict:
    """Get current weights with fallback."""
    try:
        from model_updater import get_current_weights
        return await get_current_weights(db)
    except:
        return {
            'person_importance': 0.3,
            'cluster_pattern': 0.2,
            'content_urgency': 0.25,
            'learned_patterns': 0.15,
            'domain_signal': 0.1
        }


async def identify_weak_areas(db, metrics: Dict) -> list:
    """
    Identify areas where agent is underperforming.
    These become targets for focused exploration.
    """
    
    weak_areas = []
    
    # Check overall accuracy
    if metrics['accuracy_week_1'] < 0.7:
        weak_areas.append({
            'area': 'overall_accuracy',
            'current_value': metrics['accuracy_week_1'],
            'target_value': 0.85,
            'recommendation': 'Need more exploration to discover better strategies'
        })
    
    # Check if asking user too often
    if metrics['asks_user_rate_week_1'] > 0.3:
        weak_areas.append({
            'area': 'user_intervention_rate',
            'current_value': metrics['asks_user_rate_week_1'],
            'target_value': 0.1,
            'recommendation': 'Need more confident decision rules'
        })
    
    # Check exploration success rate
    if metrics['exploration_success_rate'] < 0.3:
        weak_areas.append({
            'area': 'exploration_quality',
            'current_value': metrics['exploration_success_rate'],
            'target_value': 0.5,
            'recommendation': 'Exploration hypotheses are too random - need better generation'
        })
    
    # Check if stagnant
    if metrics['accuracy_trend'] == 'stagnant':
        weak_areas.append({
            'area': 'learning_plateau',
            'recommendation': 'Need to explore different strategy space'
        })
    
    # Check specific relationship types
    relationship_accuracy = await get_accuracy_by_relationship_type(db)
    for rel_type, accuracy in relationship_accuracy.items():
        if accuracy < 0.6:
            weak_areas.append({
                'area': f'relationship_type_{rel_type}',
                'current_value': accuracy,
                'target_value': 0.8,
                'recommendation': f'Need focused exploration on {rel_type} emails'
            })
    
    return weak_areas


async def get_accuracy_by_relationship_type(db) -> Dict[str, float]:
    """Get accuracy broken down by relationship type."""
    
    # Get recent decisions
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    decisions = []
    
    for doc in db.collection('agent_decisions').where('timestamp', '>=', cutoff).stream():
        data = doc.to_dict()
        if 'feedback' in data:
            decisions.append(data)
    
    # Group by relationship type
    by_relationship = {}
    
    for decision in decisions:
        rel_type = decision.get('person_context', {}).get('relationship', {}).get('relationship_type', 'unknown')
        
        if rel_type not in by_relationship:
            by_relationship[rel_type] = {'correct': 0, 'total': 0}
        
        by_relationship[rel_type]['total'] += 1
        if decision.get('feedback', {}).get('correct') == True:
            by_relationship[rel_type]['correct'] += 1
    
    # Calculate accuracy for each
    accuracy_by_type = {}
    for rel_type, stats in by_relationship.items():
        if stats['total'] > 0:
            accuracy_by_type[rel_type] = stats['correct'] / stats['total']
    
    return accuracy_by_type


async def deprecate_underperforming_rules(db) -> int:
    """
    Find and deprecate rules that are not performing well.
    
    CRITICAL: Self-learning means FORGETTING what doesn't work.
    """
    
    deprecated = 0
    
    # Get all active rules
    active_rules = []
    for doc in db.collection('learned_rules').where('status', '==', 'active').stream():
        active_rules.append({
            'id': doc.id,
            **doc.to_dict()
        })
    
    # Check performance of each rule
    for rule in active_rules:
        performance = await get_rule_performance(db, rule['id'])
        
        # Deprecate if:
        # 1. Used at least 10 times AND accuracy < 50%
        # 2. Created >30 days ago and never used
        
        if performance['times_used'] >= 10 and performance['accuracy'] < 0.5:
            await deprecate_failing_rule(
                db, 
                rule['id'], 
                f"Low accuracy: {performance['accuracy']:.1%} over {performance['times_used']} uses"
            )
            deprecated += 1
        
        elif performance['times_used'] == 0:
            created_at = datetime.fromisoformat(rule.get('created_at', datetime.utcnow().isoformat()))
            age_days = (datetime.utcnow() - created_at).days
            
            if age_days > 30:
                await deprecate_failing_rule(
                    db,
                    rule['id'],
                    f"Never used in {age_days} days - likely not applicable"
                )
                deprecated += 1
    
    return deprecated


@weave.op()
async def start_learning_loop_background(db, interval_hours: int = 6):
    """
    Start continuous learning loop in background.
    Call this when agent starts.
    """
    
    task = asyncio.create_task(continuous_learning_loop(db, interval_hours))
    print("✅ Background learning loop started")
    return task


if __name__ == '__main__':
    # For testing: run learning loop
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Initialize Firebase
    cred = credentials.Certificate('../convo/firebase-service-account.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    
    # Initialize Weave
    weave.init('email-agent')
    
    # Run learning loop
    asyncio.run(continuous_learning_loop(db, interval_hours=1))  # Every hour for testing
