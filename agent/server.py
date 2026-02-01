"""
Agent Server - HTTP wrapper for the Python agent
Allows Node.js Discord bot to call the agent via HTTP
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import process_email
from agent import db

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "inscriptum-agent"})

@app.route('/process-email', methods=['POST'])
def process_email_endpoint():
    """
    Process a single email through the agent
    
    Request body:
    {
        "id": "email_id",
        "from": "sender@example.com",
        "to": "user@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    Returns:
    {
        "status": "success",
        "decision": {
            "action": "reply|star|archive|ignore",
            "confidence": 0.85,
            "reasoning": "...",
            "is_urgent": false,
            "is_time_sensitive": false
        }
    }
    """
    try:
        email_data = request.get_json()
        
        if not email_data:
            return jsonify({"status": "error", "error": "No email data provided"}), 400
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_email(email_data))
        loop.close()
        
        # Extract decision for Discord bot
        decision = result.get('decision', {})
        
        # Map agent actions to Discord bot actions
        action_mapping = {
            'respond': 'reply',
            'star': 'star',
            'archive': 'archive',
            'ignore': 'ignore',
            'defer': 'star',  # Defer = star for later
            'delete': 'ignore'
        }
        
        agent_action = decision.get('action', 'star')
        mapped_action = action_mapping.get(agent_action, agent_action)
        
        return jsonify({
            "status": "success",
            "decision": {
                "action": mapped_action,
                "confidence": decision.get('confidence', 0.5),
                "reasoning": decision.get('reason', decision.get('reasoning', 'No reasoning provided')),
                "is_urgent": result.get('importance', {}).get('is_urgent', False),
                "is_time_sensitive": result.get('importance', {}).get('is_time_sensitive', False),
                "learned_rule_id": decision.get('learned_rule_id'),
                "is_exploration": result.get('exploration_metadata', {}).get('is_exploration', False)
            },
            "decision_id": result.get('decision_id'),
            "importance": result.get('importance', {}),
            "generated_response": result.get('generated_response')
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/generate-draft', methods=['POST'])
def generate_draft_endpoint():
    """
    Generate a draft response for an email
    
    Request body:
    {
        "email": {...email data...},
        "user_message": "what the user wants to say"
    }
    
    Returns:
    {
        "status": "success",
        "draft": "generated response text"
    }
    """
    try:
        data = request.get_json()
        email_data = data.get('email')
        user_message = data.get('user_message', '')
        
        if not email_data:
            return jsonify({"status": "error", "error": "No email data provided"}), 400
        
        # Import here to avoid circular imports
        from agent.response_generator import generate_contextual_response
        from agent.style_learning import get_style_for_recipient
        from agent.people_graph import get_person_context
        from agent.importance import predict_importance
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get context
        sender = email_data.get('from', '')
        person_context = loop.run_until_complete(get_person_context(sender, db))
        importance = loop.run_until_complete(predict_importance(email_data, person_context, db))
        style = loop.run_until_complete(get_style_for_recipient(sender, db))
        
        # Generate response with user's intent
        # Add user_message to email data for context
        email_with_intent = {**email_data, 'user_intent': user_message}
        
        result = loop.run_until_complete(
            generate_contextual_response(email_with_intent, person_context, importance, style, db)
        )
        loop.close()
        
        # Extract the draft text
        draft_text = result.get('body', result.get('text', 'Unable to generate draft'))
        
        return jsonify({
            "status": "success",
            "draft": draft_text,
            "subject": result.get('subject', f"Re: {email_data.get('subject', '')}")
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Inscriptum Agent Server...")
    print("📡 Listening on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
