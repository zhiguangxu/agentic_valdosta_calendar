#!/usr/bin/env python3
"""Check what the Feb 26 and Mar 19 duplicate events actually look like"""

import sys
import os

# Set up path
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend')

# Set environment variable to suppress other output
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

try:
    from generic_scraper import scrape_events
    import json

    # Read sources
    with open('/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend/sources.json', 'r') as f:
        sources_data = json.load(f)

    all_events = []

    # Scrape from all event sources
    for source in sources_data['sources']:
        if source['type'] == 'events' and source['enabled']:
            print(f"\n{'='*80}")
            print(f"Scraping: {source['name']}")
            print(f"URL: {source['url']}")
            print('='*80)

            events = scrape_events(source['url'], source['type'])

            # Look for Feb 26 and Mar 19 events
            for event in events:
                start = event.get('start', '')
                if '2026-02-26' in start or '2026-03-19' in start:
                    all_events.append({
                        'source': source['name'],
                        'title': event.get('title', ''),
                        'start': event.get('start', ''),
                        'description': event.get('description', ''),
                        'url': event.get('url', '')
                    })
                    print(f"\n  Found: {event.get('title', 'NO TITLE')[:60]}")
                    print(f"  Date: {start}")

    print("\n" + "="*80)
    print("DETAILED EVENT COMPARISON")
    print("="*80)

    # Group by date
    feb26_events = [e for e in all_events if '2026-02-26' in e['start']]
    mar19_events = [e for e in all_events if '2026-03-19' in e['start']]

    print("\n\n### FEBRUARY 26 EVENTS ###")
    for i, event in enumerate(feb26_events, 1):
        print(f"\n--- Event {i} ---")
        print(f"Source: {event['source']}")
        print(f"Title: {event['title']}")
        print(f"Start: {event['start']}")
        print(f"URL: {event['url']}")
        print(f"Description: {event['description'][:300]}...")
        print(f"Description length: {len(event['description'])} chars")

    print("\n\n### MARCH 19 EVENTS ###")
    for i, event in enumerate(mar19_events, 1):
        print(f"\n--- Event {i} ---")
        print(f"Source: {event['source']}")
        print(f"Title: {event['title']}")
        print(f"Start: {event['start']}")
        print(f"URL: {event['url']}")
        print(f"Description: {event['description'][:300]}...")
        print(f"Description length: {len(event['description'])} chars")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
