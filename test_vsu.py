"""Test VSU Concert Calendar scraping"""
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

# Setup OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
print(f"Testing: {url}")
print("="*80)

if client:
    events = generic_scraper.scrape_with_ai(url, 'events', client, 'ai_twostage')
    print(f"\nExtracted {len(events)} events:")
    for event in events:
        print(f"\nTitle: {event['title']}")
        print(f"Date: {event['start']}")
        print(f"Description: {event.get('description', '')[:150]}...")
        print(f"URL: {event['url']}")
else:
    print("OpenAI client not available")
