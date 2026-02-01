"""
Style Learning Module - Communication style analysis
Learns the user's writing style and preferences
"""

import weave
from groq import Groq
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import re
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


@weave.op()
async def analyze_communication_style(db) -> Dict[str, Any]:
    """
    Analyze the user's communication style from sent emails.
    
    Learns:
    - Tone and formality level
    - Common phrases and greetings
    - Response length patterns
    - Signature style
    
    Args:
        db: Firestore client
    
    Returns:
        Style profile with learned patterns
    """
    print("\n" + "="*60)
    print("✍️ ANALYZING COMMUNICATION STYLE")
    print("="*60)
    
    # Fetch emails where user replied (these show user's writing)
    replied_emails = []
    docs = db.collection('emails').where('has_reply', '==', True).stream()
    
    for doc in docs:
        data = doc.to_dict()
        replied_emails.append(data)
    
    print(f"📝 Found {len(replied_emails)} emails with user replies")
    
    if not replied_emails:
        return {
            "status": "insufficient_data",
            "message": "No replied emails found to analyze style",
            "style_profile": get_default_style_profile()
        }
    
    # Analyze patterns
    style_profile = await extract_style_patterns(replied_emails)
    
    # Store in Firebase
    style_profile["created_at"] = datetime.utcnow().isoformat()
    db.collection('learned_patterns').document('communication_style').set(style_profile)
    
    print(f"✅ Style profile created")
    print(f"   - Formality: {style_profile.get('formality_level', 'unknown')}")
    print(f"   - Tone: {style_profile.get('tone', 'unknown')}")
    
    return {
        "status": "success",
        "emails_analyzed": len(replied_emails),
        "style_profile": style_profile
    }


def get_default_style_profile() -> Dict[str, Any]:
    """Return a default style profile when no data is available."""
    return {
        "formality_level": "semi-formal",
        "tone": "professional",
        "greeting_style": "Hi [Name],",
        "closing_style": "Best regards,",
        "avg_response_length": "medium",
        "uses_emoji": False,
        "punctuation_style": "standard",
        "paragraph_preference": "short"
    }


@weave.op()
async def extract_style_patterns(emails: List[Dict]) -> Dict[str, Any]:
    """Extract writing style patterns from emails."""
    
    style = {
        "formality_level": "semi-formal",
        "tone": "professional",
        "greeting_patterns": [],
        "closing_patterns": [],
        "avg_response_length": "medium",
        "uses_emoji": False,
        "punctuation_style": "standard",
        "common_phrases": [],
        "vocabulary_level": "professional"
    }
    
    # Collect text samples (snippets and bodies)
    text_samples = []
    for email in emails:
        text = email.get('body') or email.get('snippet', '')
        if text:
            text_samples.append(text)
    
    if not text_samples:
        return style
    
    # Analyze with LLM for sophisticated patterns
    sample_text = '\n---\n'.join(text_samples[:5])  # Use first 5 samples
    
    prompt = f"""Analyze these email samples and extract the writing style:

{sample_text[:3000]}

Respond in JSON with these fields:
{{
    "formality_level": "formal|semi-formal|informal",
    "tone": "professional|friendly|casual|direct|warm",
    "greeting_pattern": "the typical greeting used",
    "closing_pattern": "the typical closing used",
    "response_length": "short|medium|long",
    "uses_emoji": true/false,
    "punctuation_style": "minimal|standard|expressive",
    "common_phrases": ["list", "of", "common", "phrases"],
    "vocabulary_level": "simple|professional|technical"
}}

Respond with ONLY the JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You analyze writing styles. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        llm_analysis = json.loads(response.choices[0].message.content)
        style.update(llm_analysis)
        
    except Exception as e:
        print(f"⚠️ LLM style analysis error: {e}")
    
    # Also do some basic text analysis
    all_text = ' '.join(text_samples)
    
    # Check for emoji usage
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        flags=re.UNICODE
    )
    if emoji_pattern.search(all_text):
        style["uses_emoji"] = True
    
    # Analyze exclamation usage
    exclamation_count = all_text.count('!')
    question_count = all_text.count('?')
    word_count = len(all_text.split())
    
    if word_count > 0:
        exclamation_rate = exclamation_count / word_count
        if exclamation_rate > 0.05:
            style["punctuation_style"] = "expressive"
        elif exclamation_rate < 0.01:
            style["punctuation_style"] = "minimal"
    
    return style


@weave.op()
async def get_style_for_recipient(recipient_email: str, db) -> Dict[str, Any]:
    """
    Get the appropriate writing style for a specific recipient.
    Combines global style with recipient-specific adjustments.
    
    Args:
        recipient_email: Email address of the recipient
        db: Firestore client
    
    Returns:
        Style profile tailored for this recipient
    """
    # Get global style
    global_style_doc = db.collection('learned_patterns').document('communication_style').get()
    
    if global_style_doc.exists:
        global_style = global_style_doc.to_dict()
    else:
        global_style = get_default_style_profile()
    
    # Get recipient's person profile
    if '<' in recipient_email:
        recipient_email = recipient_email.split('<')[1].split('>')[0]
    recipient_email = recipient_email.lower().strip()
    
    doc_id = recipient_email.replace('@', '_at_').replace('.', '_')
    person_doc = db.collection('people').document(doc_id).get()
    
    if not person_doc.exists:
        return global_style
    
    person = person_doc.to_dict()
    relationship = person.get('relationship', {})
    
    # Adjust style based on relationship
    adjusted_style = global_style.copy()
    
    # Adjust formality based on relationship type
    rel_type = relationship.get('type', 'unknown')
    rel_formality = relationship.get('formality_level', 'semi-formal')
    
    if rel_type == 'personal':
        adjusted_style['formality_level'] = 'informal'
        adjusted_style['tone'] = 'friendly'
    elif rel_type == 'work':
        adjusted_style['formality_level'] = rel_formality
    elif rel_type == 'commercial':
        adjusted_style['formality_level'] = 'formal'
        adjusted_style['tone'] = 'professional'
    
    # Adjust greeting based on known name
    name = person.get('name')
    if name:
        if adjusted_style['formality_level'] == 'informal':
            adjusted_style['greeting'] = f"Hey {name.split()[0]},"
        elif adjusted_style['formality_level'] == 'formal':
            adjusted_style['greeting'] = f"Dear {name},"
        else:
            adjusted_style['greeting'] = f"Hi {name.split()[0]},"
    else:
        adjusted_style['greeting'] = "Hi,"
    
    return adjusted_style


@weave.op()
async def learn_style_from_feedback(email_id: str, feedback: str, db) -> None:
    """
    Update style profile based on user feedback.
    
    Args:
        email_id: The email that was modified
        feedback: What the user changed
        db: Firestore client
    """
    # Get current style
    style_doc = db.collection('learned_patterns').document('communication_style').get()
    
    if not style_doc.exists:
        return
    
    style = style_doc.to_dict()
    
    # Add feedback to history
    feedback_history = style.get('feedback_history', [])
    feedback_history.append({
        "email_id": email_id,
        "feedback": feedback,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Keep only last 50 feedbacks
    if len(feedback_history) > 50:
        feedback_history = feedback_history[-50:]
    
    style['feedback_history'] = feedback_history
    style['updated_at'] = datetime.utcnow().isoformat()
    
    # Re-analyze style patterns periodically
    if len(feedback_history) % 10 == 0:
        print("🔄 Re-analyzing style based on feedback...")
        # This would trigger a re-analysis of recent interactions
    
    db.collection('learned_patterns').document('communication_style').set(style)


@weave.op()
async def adapt_text_to_style(text: str, style: Dict[str, Any]) -> str:
    """
    Adapt generated text to match the user's style.
    
    Args:
        text: The generated text
        style: The style profile to match
    
    Returns:
        Text adapted to the style
    """
    prompt = f"""Rewrite this text to match the following style:

Original text:
{text}

Style requirements:
- Formality: {style.get('formality_level', 'semi-formal')}
- Tone: {style.get('tone', 'professional')}
- Length preference: {style.get('avg_response_length', 'medium')}
- Use emoji: {style.get('uses_emoji', False)}
- Punctuation style: {style.get('punctuation_style', 'standard')}

Keep the same meaning but adjust the style. Respond with ONLY the rewritten text."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Style adaptation error: {e}")
        return text  # Return original if adaptation fails
