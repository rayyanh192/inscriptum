"""Initialize the agent by bootstrapping from Gmail history."""

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

from agent import initialize_agent

async def run():
    print("Starting agent initialization...")
    print("This will:")
    print("  1. Learn from Gmail history (bootstrap)")
    print("  2. Analyze communication style")
    print("  3. Cluster relationships")
    print()
    
    result = await initialize_agent()
    
    print()
    print("="*60)
    print("INITIALIZATION COMPLETE")
    print("="*60)
    print(f"Status: {result['status']}")
    print()
    print("Bootstrap:")
    bootstrap = result.get('bootstrap', {})
    print(f"  - People created: {bootstrap.get('people_created', 0)}")
    print(f"  - Patterns learned: {bootstrap.get('patterns_learned', 0)}")
    print()
    print("Style:")
    style = result.get('style', {})
    print(f"  - Status: {style.get('status', 'unknown')}")
    print()
    print("Clusters:")
    clusters = result.get('clusters', {})
    print(f"  - Total clusters: {clusters.get('total_clusters', 0)}")
    print(f"  - Total people: {clusters.get('total_people', 0)}")

if __name__ == "__main__":
    asyncio.run(run())
