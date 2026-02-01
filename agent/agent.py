"""
Email Agent - Main orchestrator
Self-learning email assistant with people graphing
"""

import weave
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from package
from . import db
from .decisions import analyze_email_intent, decide_action, decide_with_full_context
from .execution import store_decision, get_pending_decisions
from .people_graph import (
    analyze_person, 
    get_person_context, 
    get_cluster_context,
    cluster_relationships,
    update_person_after_action
)
from .importance import predict_importance, rank_emails_by_importance
from .style_learning import get_style_for_recipient, analyze_communication_style
from .response_generator import generate_contextual_response, generate_quick_replies
from .bootstrap import bootstrap_from_gmail_history
from .feedback import record_feedback, get_feedback_statistics
from .exploration import should_explore, generate_alternative_strategy, store_hypothesis
from .model_updater import apply_learned_rules_to_decision


@weave.op()
async def process_email(email: Dict) -> Dict[str, Any]:
    """
    Main entry point for processing a single email.
    
    SELF-LEARNING PIPELINE:
    1. Get/create person context for sender
    2. Get cluster context for relationship type
    3. Predict importance (base prediction)
    4. Apply learned rules (override if agent has learned better strategy)
    5. EXPLORE: Try alternative strategies when uncertain
    6. Analyze intent
    7. Make final action decision
    8. Generate response if needed
    9. Store decision with exploration metadata for feedback loop
    
    Args:
        email: Email data from Firebase
    
    Returns:
        Complete processing result with decision
    """
    email_id = email.get('id', 'unknown')
    sender = email.get('from', '')
    subject = email.get('subject', '')
    
    print(f"\n{'='*60}")
    print(f"📧 Processing: {subject[:50]}...")
    print(f"   From: {sender[:40]}...")
    print(f"{'='*60}")
    
    try:
        # Step 1: Get or create person context
        person_context = await get_person_context(sender, db)
        if not person_context:
            # Create new person profile
            person_context = await analyze_person(sender, [email], db)
        
        print(f"👤 Person: {person_context.get('name', 'Unknown')} "
              f"(importance: {person_context.get('importance_score', 0.5):.2f})")
        
        # Step 2: Get cluster context for this relationship type
        relationship_type = person_context.get('relationship', {}).get('type', 'unknown')
        cluster_context = await get_cluster_context(relationship_type, db)
        person_context['cluster_context'] = cluster_context
        
        print(f"👥 Cluster: {relationship_type} - {cluster_context.get('patterns', 'No patterns')}")
        
        # Step 3: Predict importance (BASE PREDICTION)
        importance = await predict_importance(email, person_context, db)
        print(f"⚡ Base Importance: {importance['importance_level']} "
              f"(score: {importance['importance_score']:.2f})")
        
        # Step 4: Analyze intent
        intent = await analyze_email_intent(email)
        print(f"🎯 Intent: {intent['intent']} "
              f"(confidence: {intent['confidence']:.2f})")
        
        # Step 5: Make BASE decision
        base_decision = await decide_action(email, intent, person_context, importance)
        print(f"🤖 Base Decision: {base_decision['action']} - {base_decision['reason'][:50]}...")
        
        # Step 6: Apply learned rules (AGENT USES WHAT IT DISCOVERED)
        decision = await apply_learned_rules_to_decision(
            email, person_context, cluster_context, base_decision, db
        )
        
        if decision.get('learned_rule_id'):
            print(f"🧠 USING LEARNED RULE: {decision['reasoning']}")
        else:
            print(f"✅ Final Decision: {decision['action']}")
        
        # Step 7: EXPLORATION - Try alternatives when uncertain
        exploration_metadata = None
        if await should_explore(email, decision, db):
            print(f"🔬 EXPLORING: Low confidence, trying alternative strategy...")
            
            alternative = await generate_alternative_strategy(
                email, decision, person_context, db
            )
            
            # USE THE EXPLORATION (generate_alternative_strategy already stores hypothesis)
            decision = alternative  # This IS the full decision dict
            exploration_metadata = {
                'is_exploration': True,
                'hypothesis_id': alternative.get('hypothesis_id'),
                'base_decision': base_decision,
                'exploration_reason': alternative.get('hypothesis', '')
            }
            
            print(f"🧪 TRYING: {decision['action']} - Hypothesis: {alternative.get('hypothesis', '')[:60]}...")
        
        # Step 8: Generate response if needed
        generated_response = None
        if decision['action'] == 'respond':
            style = await get_style_for_recipient(sender, db)
            generated_response = await generate_contextual_response(
                email, person_context, importance, style, db
            )
            print(f"📝 Generated response: {generated_response.get('subject', 'N/A')}")
        
        # Step 5: Generate response if needed
        generated_response = None
        if decision['action'] == 'respond':
            style = await get_style_for_recipient(sender, db)
            generated_response = await generate_contextual_response(
                email, person_context, importance, style, db
            )
            print(f"📝 Generated response: {generated_response.get('subject', 'N/A')}")
        
        # Step 9: Store decision for Discord bot (WITH EXPLORATION METADATA)
        result = await store_decision(
            email_id=email_id,
            email_data=email,
            intent_analysis=intent,
            decision=decision,
            importance=importance,
            person_context=person_context,
            generated_response=generated_response
        )
        
        # Add exploration metadata if this was an exploration
        if exploration_metadata:
            db.collection('agent_decisions').document(result['decision_id']).update({
                'exploration_metadata': exploration_metadata
            })
        
        print(f"💾 Stored decision: {result['decision_id']}")
        
        # Step 10: Update person profile with this interaction
        await update_person_after_action(sender, decision['action'], db)
        
        return {
            "status": "success",
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "intent": intent,
            "importance": importance,
            "decision": decision,
            "exploration_metadata": exploration_metadata,
            "generated_response": generated_response,
            "decision_id": result['decision_id'],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error processing email: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "email_id": email_id,
            "error": str(e)
        }


@weave.op()
async def process_inbox(limit: int = 10) -> Dict[str, Any]:
    """
    Process multiple unread emails from the inbox.
    
    Fetches emails from Firebase, ranks by importance,
    and processes each one.
    
    Args:
        limit: Maximum number of emails to process
    
    Returns:
        Summary of processing results
    """
    print(f"\n{'='*60}")
    print(f"📬 PROCESSING INBOX (limit: {limit})")
    print(f"{'='*60}")
    
    # Fetch unread emails
    emails = []
    docs = db.collection('emails').where('is_read', '==', False).limit(limit * 2).stream()
    
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        emails.append(data)
    
    if not emails:
        print("📭 No unread emails to process")
        return {"status": "empty", "processed": 0}
    
    print(f"📧 Found {len(emails)} unread emails")
    
    # Rank by importance
    ranked_emails = await rank_emails_by_importance(emails, db)
    
    # Process top emails
    results = []
    for email in ranked_emails[:limit]:
        result = await process_email(email)
        results.append(result)
    
    # Summary
    successful = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] == 'error']
    
    print(f"\n{'='*60}")
    print(f"✨ INBOX PROCESSING COMPLETE")
    print(f"   Processed: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Errors: {len(errors)}")
    print(f"{'='*60}")
    
    return {
        "status": "complete",
        "total_processed": len(results),
        "successful": len(successful),
        "errors": len(errors),
        "results": results
    }


@weave.op()
async def initialize_agent() -> Dict[str, Any]:
    """
    Initialize the agent with cold-start learning.
    
    Should be called once when setting up for a new user.
    """
    print(f"\n{'='*60}")
    print(f"🚀 INITIALIZING EMAIL AGENT")
    print(f"{'='*60}")
    
    # Step 1: Bootstrap from Gmail history
    bootstrap_result = await bootstrap_from_gmail_history(db)
    
    # Step 2: Analyze communication style
    style_result = await analyze_communication_style(db)
    
    # Step 3: Cluster relationships
    cluster_result = await cluster_relationships(db)
    
    return {
        "status": "initialized",
        "bootstrap": bootstrap_result,
        "style": style_result,
        "clusters": cluster_result,
        "timestamp": datetime.utcnow().isoformat()
    }


@weave.op()
async def get_agent_status() -> Dict[str, Any]:
    """
    Get current agent status and statistics.
    """
    # Count people profiles
    people_count = len(list(db.collection('people').stream()))
    
    # Count emails
    emails_count = len(list(db.collection('emails').stream()))
    
    # Count decisions
    decisions_count = len(list(db.collection('agent_decisions').stream()))
    
    # Get feedback statistics
    feedback_stats = await get_feedback_statistics(db)
    
    # Get learned patterns
    patterns_doc = db.collection('learned_patterns').document('importance').get()
    patterns = patterns_doc.to_dict() if patterns_doc.exists else {}
    
    return {
        "status": "active",
        "statistics": {
            "people_profiles": people_count,
            "emails_analyzed": emails_count,
            "decisions_made": decisions_count
        },
        "feedback": feedback_stats.get('metrics', {}),
        "learned_patterns": len(patterns.get('rules', [])),
        "timestamp": datetime.utcnow().isoformat()
    }


# Legacy compatibility
async def handle_email(email_id: str, email_data: dict) -> dict:
    """Legacy entry point - wraps process_email."""
    email_data['id'] = email_id
    return await process_email(email_data)
