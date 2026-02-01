"""
Response Generator Module - Contextual reply generation
Generates personalized email responses based on learned style
"""

import weave
from groq import Groq
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def generate_contextual_response(
    email: Dict,
    person_context: Optional[Dict],
    importance: Dict,
    style: Dict,
    db
) -> Dict[str, Any]:
    """
    Generate a contextual email response.
    
    Uses:
    - Person context (relationship, history)
    - Importance prediction (urgency)
    - Learned style (tone, formality)
    - Email content (subject, body)
    
    Args:
        email: The email to respond to
        person_context: Context about the sender
        importance: Importance prediction
        style: Writing style profile
        db: Firestore client
    
    Returns:
        Generated response with metadata
    """
    # Build context for generation
    context = build_generation_context(email, person_context, importance, style)
    
    # Generate the response
    response = await generate_response_with_llm(context)
    
    # Apply style adjustments if needed
    if style.get('formality_level') or style.get('tone'):
        from .style_learning import adapt_text_to_style
        response['body'] = await adapt_text_to_style(response['body'], style)
    
    # Add metadata
    response['metadata'] = {
        "generated_at": datetime.utcnow().isoformat(),
        "original_email_id": email.get('id'),
        "person_context_used": person_context is not None,
        "importance_level": importance.get('importance_level', 'medium'),
        "style_applied": style.get('formality_level', 'semi-formal')
    }
    
    # Store generated response for feedback
    doc_ref = db.collection('generated_responses').document()
    response['id'] = doc_ref.id
    doc_ref.set(response)
    
    return response


def build_generation_context(
    email: Dict,
    person_context: Optional[Dict],
    importance: Dict,
    style: Dict
) -> Dict[str, Any]:
    """Build context object for response generation."""
    
    context = {
        "email": {
            "from": email.get('from', ''),
            "subject": email.get('subject', ''),
            "snippet": email.get('snippet', ''),
            "body": email.get('body', '')[:2000] if email.get('body') else ''
        },
        "style": {
            "formality": style.get('formality_level', 'semi-formal'),
            "tone": style.get('tone', 'professional'),
            "greeting": style.get('greeting', 'Hi,'),
            "closing": style.get('closing_pattern', 'Best regards,'),
            "uses_emoji": style.get('uses_emoji', False)
        },
        "urgency": importance.get('importance_level', 'medium'),
        "action_items": importance.get('content_analysis', {}).get('action_items', [])
    }
    
    if person_context:
        context["sender"] = {
            "name": person_context.get('name'),
            "relationship_type": person_context.get('relationship', {}).get('type', 'unknown'),
            "relationship_category": person_context.get('relationship', {}).get('category', 'other'),
            "expected_response_time": person_context.get('relationship', {}).get('expected_response_time', 'few_days'),
            "importance_score": person_context.get('importance_score', 0.5)
        }
    
    return context


@weave.op()
async def generate_response_with_llm(context: Dict) -> Dict[str, Any]:
    """Generate email response using LLM."""
    
    email = context['email']
    style = context['style']
    sender = context.get('sender', {})
    
    # Build prompt
    sender_name = sender.get('name', 'the sender')
    relationship = sender.get('relationship_type', 'unknown')
    
    prompt = f"""Generate an email response with the following requirements:

ORIGINAL EMAIL:
From: {email['from']}
Subject: {email['subject']}
Content: {email['snippet'] or email['body'][:500]}

STYLE REQUIREMENTS:
- Formality: {style['formality']}
- Tone: {style['tone']}
- Use greeting: {style['greeting']}
- Use closing: {style['closing']}
- Include emoji: {style['uses_emoji']}

CONTEXT:
- Sender relationship: {relationship}
- Urgency level: {context['urgency']}
- Action items to address: {context.get('action_items', [])}

Generate a complete email response that:
1. Addresses the main points of the original email
2. Matches the required style and tone
3. Is concise but complete
4. Uses appropriate greeting and closing

Respond in JSON format:
{{
    "subject": "Re: [appropriate subject]",
    "body": "The full email body",
    "key_points_addressed": ["list", "of", "points"]
}}

Respond with ONLY the JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an email assistant that writes responses matching the user's style. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "subject": result.get('subject', f"Re: {email['subject']}"),
            "body": result.get('body', ''),
            "key_points_addressed": result.get('key_points_addressed', [])
        }
        
    except Exception as e:
        print(f"⚠️ Response generation error: {e}")
        return {
            "subject": f"Re: {email['subject']}",
            "body": f"Thank you for your email. I will review and respond shortly.\n\n{style['closing']}",
            "key_points_addressed": [],
            "error": str(e)
        }


@weave.op()
async def generate_quick_replies(
    email: Dict,
    person_context: Optional[Dict],
    db
) -> List[Dict[str, str]]:
    """
    Generate quick reply options for an email.
    
    Returns 3 short response options.
    """
    subject = email.get('subject', '')
    snippet = email.get('snippet', '')
    
    relationship = 'unknown'
    if person_context:
        relationship = person_context.get('relationship', {}).get('type', 'unknown')
    
    prompt = f"""Generate 3 quick reply options for this email:

Subject: {subject}
Content: {snippet}
Relationship: {relationship}

Provide 3 short responses (1-2 sentences each) with different tones:
1. Positive/agreeing
2. Neutral/acknowledging
3. Declining/postponing (if applicable)

Respond in JSON:
{{
    "replies": [
        {{"type": "positive", "text": "..."}},
        {{"type": "neutral", "text": "..."}},
        {{"type": "declining", "text": "..."}}
    ]
}}

Respond with ONLY the JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Generate quick email replies. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get('replies', [])
        
    except Exception as e:
        print(f"⚠️ Quick reply generation error: {e}")
        return [
            {"type": "positive", "text": "Thanks for reaching out! I'll get back to you soon."},
            {"type": "neutral", "text": "Received, thank you."},
            {"type": "declining", "text": "Thanks for your email. I'll need some time to review this."}
        ]


@weave.op()
async def improve_draft(
    draft: str,
    improvement_type: str,
    style: Dict,
    db
) -> Dict[str, Any]:
    """
    Improve an existing draft based on user request.
    
    Args:
        draft: The current draft text
        improvement_type: Type of improvement (shorten, expand, formalize, casual, clarify)
        style: User's style profile
        db: Firestore client
    
    Returns:
        Improved draft with explanation
    """
    improvement_prompts = {
        "shorten": "Make this email more concise while keeping the key points",
        "expand": "Expand on the key points with more detail and context",
        "formalize": "Make this email more formal and professional",
        "casual": "Make this email more casual and friendly",
        "clarify": "Make this email clearer and easier to understand"
    }
    
    instruction = improvement_prompts.get(improvement_type, improvement_type)
    
    prompt = f"""Improve this email draft:

ORIGINAL DRAFT:
{draft}

INSTRUCTION: {instruction}

STYLE CONTEXT:
- User's typical tone: {style.get('tone', 'professional')}
- User's formality: {style.get('formality_level', 'semi-formal')}

Respond in JSON:
{{
    "improved_draft": "the improved email text",
    "changes_made": ["list", "of", "changes"],
    "improvement_summary": "brief explanation of improvements"
}}

Respond with ONLY the JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You improve email drafts. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"⚠️ Draft improvement error: {e}")
        return {
            "improved_draft": draft,
            "changes_made": [],
            "improvement_summary": f"Unable to improve: {e}",
            "error": str(e)
        }


@weave.op()
async def record_response_feedback(
    response_id: str,
    feedback: Dict,
    db
) -> None:
    """
    Record feedback on a generated response.
    
    Args:
        response_id: ID of the generated response
        feedback: Feedback data (used/edited/discarded, edits made)
        db: Firestore client
    """
    # Get the response
    response_ref = db.collection('generated_responses').document(response_id)
    response_doc = response_ref.get()
    
    if not response_doc.exists:
        return
    
    response = response_doc.to_dict()
    
    # Add feedback
    response['feedback'] = {
        **feedback,
        "recorded_at": datetime.utcnow().isoformat()
    }
    
    response_ref.set(response)
    
    # Also record in training_feedback for learning
    db.collection('training_feedback').add({
        "type": "response_feedback",
        "response_id": response_id,
        "feedback": feedback,
        "original_email_id": response.get('metadata', {}).get('original_email_id'),
        "timestamp": datetime.utcnow().isoformat()
    })
