"""
Test script for debugging two-stage scraping
"""
import os
import sys
from openai import OpenAI

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.generic_scraper import _scrape_twostage

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

client = OpenAI(api_key=openai_api_key)

# Test Visit Valdosta
url = "https://visitvaldosta.org/events/"
print(f"Testing two-stage scraping for: {url}")
print("=" * 80)

events = _scrape_twostage(url, client)

print("\n" + "=" * 80)
print(f"\nFinal Results: {len(events)} events found")
print("=" * 80)

for i, event in enumerate(events, 1):
    print(f"\n{i}. {event['title']}")
    print(f"   Date: {event['start']}")
    print(f"   URL: {event['url']}")
    print(f"   Description: {event['description'][:100]}...")
