import weave
from groq import Groq
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any

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
1. Primary intent (e.g., 'request_action', 'share_information', 'ask_question', 'notification', 'spam')
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
async def decide_action(email_data: dict, intent_analysis: dict) -> dict:
    """
    Decide what action to take based on intent analysis.
    
    Action types:
    - 'auto': High confidence, safe to execute automatically
    - 'ask': Medium confidence or potentially risky, ask user first
    - 'notify': Low confidence or just informational, notify user only
    
    Args:
        email_data: Original email data
        intent_analysis: Results from analyze_email_intent
    
    Returns:
        Dictionary with action, reason, and suggested_response if applicable
    """
    confidence = intent_analysis.get('confidence', 0.0)
    intent = intent_analysis.get('intent', 'unknown')
    category = email_data.get('category', 'unknown')
    has_links = len(email_data.get('links', [])) > 0
    
    # Build context for LLM decision
    prompt = f"""Based on this email analysis, decide the appropriate action.

Email Info:
- Category: {category}
- Intent: {intent}
- Confidence: {confidence:.2f}
- Has Links: {has_links}
- Reasoning: {intent_analysis.get('reasoning', 'N/A')}

Action Guidelines:
- 'auto': High confidence (>0.8) AND safe intent (info sharing, notifications) AND no risky requests
- 'ask': Medium confidence (0.5-0.8) OR potentially risky actions OR money/sensitive data involved
- 'notify': Low confidence (<0.5) OR spam OR just FYI content

You must respond ONLY with valid JSON, no other text. Use this exact format:
{{
  "action": "auto|ask|notify",
  "reason": "why this action is appropriate",
  "risk_level": "low|medium|high",
  "suggested_response": "optional message to user or action to take"
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
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"Error in decide_action: {str(e)}")
        # Fallback: be conservative
        return {
            "action": "notify",
            "reason": f"Error in decision making: {str(e)}",
            "risk_level": "unknown",
            "suggested_response": "Unable to analyze - please review manually"
        }