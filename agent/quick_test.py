"""Quick test to verify all imports and basic functionality."""

import asyncio
import sys
import os

# Add parent directory to path so 'agent' can be imported as a package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weave

# Initialize Weave first
weave.init('email-agent')

print('Testing imports...')

db = None

try:
    from agent import process_email, initialize_agent, get_agent_status, db as agent_db
    db = agent_db
    print('  ✅ agent.py')
except Exception as e:
    print(f'  ❌ agent.py: {e}')

try:
    from agent.bootstrap import bootstrap_from_gmail_history
    print('  ✅ bootstrap.py')
except Exception as e:
    print(f'  ❌ bootstrap.py: {e}')

try:
    from agent.people_graph import analyze_person, cluster_relationships, get_person_context
    print('  ✅ people_graph.py')
except Exception as e:
    print(f'  ❌ people_graph.py: {e}')

try:
    from agent.style_learning import analyze_communication_style, get_style_for_recipient
    print('  ✅ style_learning.py')
except Exception as e:
    print(f'  ❌ style_learning.py: {e}')

try:
    from agent.importance import predict_importance, rank_emails_by_importance
    print('  ✅ importance.py')
except Exception as e:
    print(f'  ❌ importance.py: {e}')

try:
    from agent.response_generator import generate_contextual_response, generate_quick_replies
    print('  ✅ response_generator.py')
except Exception as e:
    print(f'  ❌ response_generator.py: {e}')

try:
    from agent.decisions import analyze_email_intent, decide_action, decide_with_full_context
    print('  ✅ decisions.py')
except Exception as e:
    print(f'  ❌ decisions.py: {e}')

try:
    from agent.execution import store_decision, get_pending_decisions
    print('  ✅ execution.py')
except Exception as e:
    print(f'  ❌ execution.py: {e}')

try:
    from agent.feedback import record_feedback, get_feedback_statistics
    print('  ✅ feedback.py')
except Exception as e:
    print(f'  ❌ feedback.py: {e}')

print('\nAll imports complete!')

# Quick status check
async def quick_test():
    if db is None:
        print('❌ Database not initialized, skipping status check')
        return
    
    print('\n📊 Getting agent status...')
    status = await get_agent_status()
    print(f'   People profiles: {status["statistics"]["people_profiles"]}')
    print(f'   Emails: {status["statistics"]["emails_analyzed"]}')
    print(f'   Decisions: {status["statistics"]["decisions_made"]}')
    print('\n✅ Agent is ready!')

asyncio.run(quick_test())
