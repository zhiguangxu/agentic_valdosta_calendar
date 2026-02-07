"""
Test both event sources and check for duplicates
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import source_manager, generic_scraper, main

# Setup OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

# Get event sources
event_sources = source_manager.get_sources_by_type('events')

all_events = []
for source in event_sources:
    if not source.get('enabled'):
        continue
    print(f"\n{'='*80}")
    print(f"Scraping: {source['name']}")
    print(f"URL: {source['url']}")
    print(f"Method: {source.get('scraping_method', 'auto')}")
    print('='*80)

    # Scrape
    url = source['url']
    source_type = source['type']
    scraping_method = source.get('scraping_method', 'auto')

    if scraping_method in ['ai', 'ai_twostage'] and client:
        events = generic_scraper.scrape_with_ai(url, source_type, client, scraping_method)
    else:
        events = generic_scraper.scrape_generic_auto(url, source_type)

    print(f"\nFound {len(events)} events from {source['name']}")
    for event in events[:5]:
        print(f"  - {event['title']} on {event['start'].split('T')[0]}")

    all_events.extend(events)

print(f"\n{'='*80}")
print(f"Total events before deduplication: {len(all_events)}")

# Deduplicate
unique_events = main.deduplicate_events(all_events)
print(f"Total events after deduplication: {len(unique_events)}")
print(f"Duplicates removed: {len(all_events) - len(unique_events)}")

# Show which events were kept
print(f"\n{'='*80}")
print("Final unique events:")
for i, event in enumerate(unique_events[:10], 1):
    print(f"{i}. {event['title']} - {event['start'].split('T')[0]}")
