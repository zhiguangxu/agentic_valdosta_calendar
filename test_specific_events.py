"""
Test specific problematic events to debug AI extraction
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

client = OpenAI(api_key=openai_api_key)

# Test specific event URLs
test_events = [
    {
        "name": "2nd Annual Black History Month Parade",
        "url": "https://www.valdostacity.com/event/2nd-annual-black-history-month-parade",
        "expected_date": "2026-02-07"
    },
    {
        "name": "South Georgia Film Festival",
        "url": "https://southgeorgiafilm.com/",
        "expected_status": "postponed",
        "original_dates": "2026-03-06 to 2026-03-07"
    },
    {
        "name": "Tea for Two @ Wildflower Cafe",
        "url": "https://www.facebook.com/events/1103274771281699",
        "expected_dates": ["2026-02-13", "2026-02-14"]
    }
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

for event in test_events:
    print(f"\n{'='*80}")
    print(f"Testing: {event['name']}")
    print(f"URL: {event['url']}")
    print(f"{'='*80}\n")

    try:
        resp = requests.get(event['url'], headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        content = str(soup.body)[:15000] if soup.body else str(soup)[:15000]

        # Show first 500 chars of content
        print("Content preview:")
        print(content[:500])
        print("\n" + "-"*80 + "\n")

    except Exception as e:
        print(f"Error fetching page: {e}\n")
