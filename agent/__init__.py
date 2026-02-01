"""
Self-Learning Email Agent with People Graphing
Powered by Weights & Biases Weave for tracing and learning
"""

import weave
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

# Initialize Weave for tracing
weave.init(project_name=os.getenv('WANDB_PROJECT', 'email-agent'))
print("✅ Weave initialized!")

# Initialize Firebase (singleton pattern)
def get_firestore_client():
    """Get or create Firestore client."""
    if not firebase_admin._apps:
        service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized!")
    return firestore.client()

# Shared database instance
db = get_firestore_client()

print("✅ Email Agent ready!")

# Export main functions from agent.py
from .agent import (
    process_email,
    process_inbox,
    initialize_agent,
    get_agent_status,
    handle_email
)