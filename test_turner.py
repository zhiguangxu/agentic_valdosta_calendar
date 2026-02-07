"""Test Turner Center scraping"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import generic_scraper

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

url = "https://turnercenter.org/mainevents/"
print(f"Testing: {url}")
print("="*80)

if client:
    events = generic_scraper.scrape_with_ai(url, 'events', client, 'ai_twostage')
    print(f"\nExtracted {len(events)} events:")
    
    # Group by month
    from collections import defaultdict
    by_month = defaultdict(list)
    for event in events:
        month = event['start'][:7]  # YYYY-MM
        by_month[month].append(event)
    
    for month in sorted(by_month.keys()):
        print(f"\n{month}: {len(by_month[month])} event(s)")
        for event in by_month[month][:5]:  # Show first 5 per month
            print(f"  - {event['title']} on {event['start'].split('T')[0]}")
            if event.get('description'):
                print(f"    {event['description'][:80]}...")
else:
    print("OpenAI client not available")
