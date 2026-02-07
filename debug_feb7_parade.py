"""Debug: Check Feb 7 parade event"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import source_manager

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

if not client:
    print("ERROR: OpenAI client not available")
    sys.exit(1)

# Get events sources
sources = source_manager.get_sources_by_type('events')
print(f"{'='*80}")
print(f"CHECKING FEB 7 EVENTS")
print(f"{'='*80}\n")

# Import scraping functions
from backend import generic_scraper

all_events = []
for source in sources:
    print(f"\nScraping: {source['name']}")
    try:
        scraping_method = source.get('scraping_method', 'auto')
        if scraping_method in ['ai', 'ai_twostage']:
            items = generic_scraper.scrape_with_ai(
                source['url'],
                source['type'],
                client,
                scraping_method
            )
        else:
            items = generic_scraper.scrape_generic_auto(source['url'], source['type'])

        print(f"  Found {len(items)} items")
        all_events.extend(items)
    except Exception as e:
        print(f"  Error: {e}")

print(f"\n{'='*80}")
print(f"SEARCHING FOR FEB 7 EVENTS")
print(f"{'='*80}\n")

feb7_events = [e for e in all_events if e.get('start', '').startswith('2026-02-07')]

print(f"Found {len(feb7_events)} events on Feb 7, 2026:\n")
for e in feb7_events:
    print(f"Title: {e.get('title')}")
    print(f"Start: {e.get('start')}")
    print(f"URL: {e.get('url', 'No URL')[:80]}")
    print(f"Description: {e.get('description', 'No description')[:150]}")
    print(f"{'-'*80}\n")
