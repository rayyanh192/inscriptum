import weave
import firebase_admin
from firebase_admin import firestore
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from decisions import analyze_email_intent, decide_action
from execution import store_decision

# Load environment variables
load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
    cred = firebase_admin.credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

@weave.op()
async def handle_email(email_id: str, email_data: dict) -> dict:
    """
    Main entry point for processing an email.
    Creates a Weave trace with child operations for intent analysis and decision making.
    
    Args:
        email_id: Unique identifier for the email
        email_data: Dictionary containing email fields:
            - from: sender email
            - subject: email subject
            - body: email body text
            - links: list of URLs found in email
            - category: email category from classifier
    
    Returns:
        Dictionary with processing result and decision
    """
    print(f"\n📧 Processing email {email_id}...")
    print(f"From: {email_data.get('from')}")
    print(f"Subject: {email_data.get('subject')}")
    print(f"Category: {email_data.get('category')}")
    
    try:
        # Step 1: Analyze email intent using LLM
        intent_analysis = await analyze_email_intent(email_data)
        print(f"\n🧠 Intent: {intent_analysis['intent']}")
        print(f"Confidence: {intent_analysis['confidence']:.2f}")
        
        # Step 2: Decide on action based on intent analysis
        decision = await decide_action(email_data, intent_analysis)
        print(f"\n✅ Decision: {decision['action']}")
        print(f"Reason: {decision['reason']}")
        
        # Step 3: Store decision in Firebase for Discord bot
        result = await store_decision(
            email_id=email_id,
            email_data=email_data,
            intent_analysis=intent_analysis,
            decision=decision
        )
        
        print(f"\n💾 Stored in Firebase: {result['decision_id']}")
        
        return {
            "status": "success",
            "email_id": email_id,
            "intent": intent_analysis['intent'],
            "confidence": intent_analysis['confidence'],
            "action": decision['action'],
            "decision_id": result['decision_id'],
            "timestamp": result['timestamp']
        }
        
    except Exception as e:
        print(f"\n❌ Error processing email: {str(e)}")
        return {
            "status": "error",
            "email_id": email_id,
            "error": str(e)
        }