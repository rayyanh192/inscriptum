"""
Decisions Module - Enhanced action selection with people context
Makes intelligent decisions about email handling
"""

import weave
from groq import Groq
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def analyze_email_intent(email_data: dict) -> dict:
    """
    Analyze email intent using Groq LLM.
    Extracts intent, confidence level, and key entities.
    
    Args:
        email_data: Dictionary with email content
    
    Returns:
        Dictionary with intent, confidence (0-1), entities, and reasoning
    """
    prompt = f"""Analyze this email and extract:
1. Primary intent (e.g., 'request_action', 'share_information', 'ask_question', 'notification', 'spam', 'newsletter', 'transactional')
2. Confidence level (0.0-1.0) in your analysis
3. Key entities (people, dates, amounts, products mentioned)
4. Brief reasoning for your analysis

Email Details:
From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Category: {email_data.get('category', 'Unknown')}
Body: {email_data.get('body', '')[:500]}...
Links: {len(email_data.get('links', []))} link(s) found

You must respond ONLY with valid JSON, no other text. Use this exact format:
{{
  "intent": "intent_type",
  "confidence": 0.85,
  "entities": {{"key": "value"}},
  "reasoning": "brief explanation"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": "You are a JSON-only API. Always respond with valid JSON and nothing else."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"Error in analyze_email_intent: {str(e)}")
        # Fallback response
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "entities": {},
            "reasoning": f"Error: {str(e)}"
        }


@weave.op()
async def decide_action(
    email_data: dict,
    intent_analysis: dict,
    person_context: Optional[Dict] = None,
    importance: Optional[Dict] = None
) -> dict:
    """
    Decide what action to take based on intent analysis AND people context.
    
    Enhanced with:
    - Person relationship awareness
    - Importance prediction
    - Historical behavior patterns
    
    Action types:
    - 'respond': Generate a response (high importance, requires reply)
    - 'archive': Archive (low importance, already read)
    - 'star': Star for later (important but not urgent)
    - 'delete': Delete (spam, unwanted)
    - 'ask': Ask user for guidance
    - 'notify': Just notify user
    
    Args:
        email_data: Original email data
        intent_analysis: Results from analyze_email_intent
        person_context: Optional context about the sender
        importance: Optional importance prediction
    
    Returns:
        Dictionary with action, reason, and additional context
    """
    confidence = intent_analysis.get('confidence', 0.0)
    intent = intent_analysis.get('intent', 'unknown')
    category = email_data.get('category', 'unknown')
    has_links = len(email_data.get('links', [])) > 0
    
    # Get person context info
    person_info = ""
    if person_context:
        relationship = person_context.get('relationship', {})
        person_info = f"""
Person Context:
- Name: {person_context.get('name', 'Unknown')}
- Relationship Type: {relationship.get('type', 'unknown')}
- Relationship Category: {relationship.get('category', 'other')}
- Importance Score: {person_context.get('importance_score', 0.5):.2f}
- Expected Response Time: {relationship.get('expected_response_time', 'unknown')}
- Reply Rate with this sender: {person_context.get('metrics', {}).get('reply_rate', 0):.2%}
- Starred Rate: {person_context.get('metrics', {}).get('starred_rate', 0):.2%}
- Delete Rate: {person_context.get('metrics', {}).get('delete_rate', 0):.2%}"""

    # Get importance info
    importance_info = ""
    if importance:
        importance_info = f"""
Importance Analysis:
- Overall Score: {importance.get('importance_score', 0.5):.2f}
- Level: {importance.get('importance_level', 'medium')}
- Requires Response: {importance.get('content_analysis', {}).get('requires_response', False)}
- Has Deadline: {importance.get('content_analysis', {}).get('deadline_mentioned', False)}
- Action Items: {len(importance.get('content_analysis', {}).get('action_items', []))}"""

    # Build context for LLM decision
    prompt = f"""Based on this comprehensive email analysis, decide the best action.

Email Info:
- From: {email_data.get('from', 'Unknown')}
- Subject: {email_data.get('subject', 'No subject')}
- Category: {category}
- Intent: {intent}
- Confidence: {confidence:.2f}
- Has Links: {has_links}
- Is Read: {email_data.get('is_read', False)}
- Is Starred: {email_data.get('is_starred', False)}
- Days Unread: {email_data.get('days_unread', 'N/A')}
{person_info}
{importance_info}

Available Actions:
- 'respond': Generate a response (for important emails that need reply)
- 'archive': Archive without action (low priority, already handled)
- 'star': Star for later review (important but not urgent)
- 'delete': Delete (spam, unwanted marketing, etc.)
- 'ask': Ask user what to do (uncertain or risky)
- 'notify': Just inform user (FYI only)

Decision Guidelines:
- High importance + requires response → 'respond'
- High delete rate with sender + spam intent → 'delete'
- Important person + not urgent → 'star'
- Low importance + already read → 'archive'
- Uncertain → 'ask'

You must respond ONLY with valid JSON:
{{
  "action": "respond|archive|star|delete|ask|notify",
  "reason": "why this action is appropriate",
  "confidence": 0.85,
  "risk_level": "low|medium|high",
  "priority": "high|medium|low",
  "suggested_response": "if action is respond, brief summary of what to say"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": "You are an intelligent email assistant. You learn from user behavior patterns to make smart decisions. Always respond with valid JSON."
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        
        # Add metadata
        result['decided_at'] = datetime.utcnow().isoformat()
        result['person_context_used'] = person_context is not None
        result['importance_used'] = importance is not None
        
        return result
        
    except Exception as e:
        print(f"Error in decide_action: {str(e)}")
        # Fallback: be conservative
        return {
            "action": "ask",
            "reason": f"Error in decision making: {str(e)}",
            "confidence": 0.0,
            "risk_level": "unknown",
            "priority": "medium",
            "suggested_response": "Unable to analyze - please review manually"
        }


@weave.op()
async def decide_with_full_context(email: Dict, db) -> Dict[str, Any]:
    """
    Make a decision using the full context pipeline.
    
    This is the main entry point that:
    1. Gets person context
    2. Predicts importance
    3. Analyzes intent
    4. Makes action decision
    
    Args:
        email: The email to process
        db: Firestore client
    
    Returns:
        Complete decision with all context
    """
    from .people_graph import get_person_context
    from .importance import predict_importance
    
    sender = email.get('from', '')
    
    # Step 1: Get person context
    person_context = await get_person_context(sender, db)
    
    # Step 2: Predict importance
    importance = await predict_importance(email, person_context, db)
    
    # Step 3: Analyze intent
    intent = await analyze_email_intent(email)
    
    # Step 4: Make decision
    decision = await decide_action(email, intent, person_context, importance)
    
    # Combine all context
    return {
        "email_id": email.get('id'),
        "sender": sender,
        "subject": email.get('subject', ''),
        "intent": intent,
        "importance": importance,
        "person_context": {
            "name": person_context.get('name') if person_context else None,
            "importance_score": person_context.get('importance_score') if person_context else None,
            "relationship": person_context.get('relationship', {}).get('type') if person_context else None
        },
        "decision": decision,
        "timestamp": datetime.utcnow().isoformat()
    }