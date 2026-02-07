"""
Debug the three issues with valdostacity events
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

# Get both event sources
event_sources = source_manager.get_sources_by_type('events')

all_events = []
for source in event_sources:
    if not source.get('enabled'):
        continue

    print(f"\n{'='*80}")
    print(f"Source: {source['name']}")
    print('='*80)

    url = source['url']
    source_type = source['type']
    scraping_method = source.get('scraping_method', 'auto')

    if scraping_method in ['ai', 'ai_twostage'] and client:
        events = generic_scraper.scrape_with_ai(url, source_type, client, scraping_method)
    else:
        events = generic_scraper.scrape_generic_auto(url, source_type)

    print(f"Extracted {len(events)} events\n")

    # Show parade events specifically
    for event in events:
        if 'parade' in event['title'].lower() or 'bird' in event['title'].lower() or 'first friday' in event['title'].lower():
            print(f"  Title: '{event['title']}'")
            print(f"  Date: {event['start']}")
            print(f"  Description: '{event.get('description', '')[:100]}...'")
            print(f"  URL: {event['url']}")
            print()

    all_events.extend(events)

print(f"\n{'='*80}")
print(f"Before deduplication: {len(all_events)} events")

# Show parade events before dedup
parade_events = [e for e in all_events if 'parade' in e['title'].lower()]
print(f"\nParade events BEFORE dedup: {len(parade_events)}")
for e in parade_events:
    print(f"  - '{e['title']}' on {e['start'].split('T')[0]}")

# Deduplicate
unique_events = main.deduplicate_events(all_events)

print(f"\nAfter deduplication: {len(unique_events)} events")
print(f"Duplicates removed: {len(all_events) - len(unique_events)}")

# Show parade events after dedup
parade_events_after = [e for e in unique_events if 'parade' in e['title'].lower()]
print(f"\nParade events AFTER dedup: {len(parade_events_after)}")
for e in parade_events_after:
    print(f"  - '{e['title']}' on {e['start'].split('T')[0]}")
