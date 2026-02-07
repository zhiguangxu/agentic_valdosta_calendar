"""Test VSU with detailed logging"""
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

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
print(f"Testing: {url}\n")

if client:
    events = generic_scraper.scrape_with_ai(url, 'events', client, 'ai_twostage')
    
    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for event in events:
        date = event['start'].split('T')[0]
        by_date[date].append(event['title'])
    
    print(f"\n{'='*80}")
    print(f"Final events grouped by date:")
    print('='*80)
    for date in sorted(by_date.keys()):
        print(f"\n{date}: {len(by_date[date])} event(s)")
        for title in by_date[date]:
            print(f"  - {title}")
    
    # Check for March events
    march_events = [e for e in events if e['start'].startswith('2026-03')]
    print(f"\n{'='*80}")
    print(f"March events: {len(march_events)}")
    if march_events:
        for e in march_events[:5]:
            print(f"  - {e['title']} on {e['start']}")
else:
    print("OpenAI client not available")
