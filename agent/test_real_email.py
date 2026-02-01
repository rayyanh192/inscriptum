"""Test processing a real email from Firebase."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before importing agent
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import asyncio
import weave
weave.init('email-agent')

from agent import process_email, db

async def test():
    # Test with a real email from Firebase
    print('Fetching first email from Firebase...')
    doc = next(db.collection('emails').limit(1).stream())
    email = doc.to_dict()
    email['id'] = doc.id
    
    print(f'Processing: {email.get("subject", "No subject")[:50]}')
    print(f'From: {email.get("from", "Unknown")[:40]}')
    
    result = await process_email(email)
    
    print()
    print('='*50)
    print('RESULT:')
    print(f'  Status: {result["status"]}')
    print(f'  Intent: {result.get("intent", {}).get("intent", "N/A")}')
    print(f'  Importance: {result.get("importance", {}).get("importance_level", "N/A")}')
    print(f'  Decision: {result.get("decision", {}).get("action", "N/A")}')

if __name__ == "__main__":
    asyncio.run(test())
