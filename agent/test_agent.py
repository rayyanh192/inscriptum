"""
Example script to test the email agent.
Run this to process a sample email through the agent pipeline.
"""

import asyncio
import weave
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Weave with W&B
weave.init(project_name=os.getenv('WANDB_PROJECT', 'email-agent'))

from agent import handle_email

async def main():
    # Sample email data
    sample_email = {
        'from': 'newsletter@techcrunch.com',
        'subject': 'Top 5 AI Startups Raising $100M+ This Week',
        'body': '''
        Hey there,
        
        Check out these incredible AI companies that just announced massive funding rounds.
        Click the links below to learn more about each company:
        
        1. DataVision AI - $150M Series C
        2. AutoML Solutions - $200M Series B
        
        Don't miss out on these insights!
        
        Best,
        TechCrunch Team
        ''',
        'links': [
            'https://techcrunch.com/datavision-funding',
            'https://techcrunch.com/automl-series-b'
        ],
        'category': 'newsletter'
    }
    
    print("=" * 60)
    print("🤖 EMAIL AGENT TEST")
    print("=" * 60)
    
    # Process the email
    result = await handle_email(
        email_id='test_email_001',
        email_data=sample_email
    )
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULT")
    print("=" * 60)
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Action: {result['action']}")
        print(f"Decision ID: {result['decision_id']}")
    else:
        print(f"Error: {result.get('error')}")

if __name__ == '__main__':
    asyncio.run(main())
