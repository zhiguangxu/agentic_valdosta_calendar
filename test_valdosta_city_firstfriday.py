#!/usr/bin/env python3
"""Test Valdosta City scraping for First Friday event"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
import os

print("Testing Valdosta City for First Friday event...")
print("="*60)

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)

# Get Valdosta City source
sources = source_manager.get_all_sources()
valdosta_city = None
for source in sources:
    if "valdostacity.com" in source['url'] and source['type'] == 'events':
        valdosta_city = source
        break

if not valdosta_city:
    print("❌ ERROR: Valdosta City source not found!")
    sys.exit(1)

print(f"Found source: {valdosta_city['name']}")
print(f"URL: {valdosta_city['url']}")
print(f"Enabled: {valdosta_city['enabled']}")
print(f"Method: {valdosta_city.get('scraping_method', 'auto')}")
print()

# Scrape it
print("Scraping Valdosta City...")
print("="*60)
events = scrape_source(valdosta_city)

print(f"\nTotal events found: {len(events)}")
print()

# Look for "First Friday" events
first_friday_events = [e for e in events if 'first friday' in e['title'].lower()]

if first_friday_events:
    print(f"✅ Found {len(first_friday_events)} 'First Friday' events:")
    for event in first_friday_events:
        print(f"  - {event['title']}")
        print(f"    Date: {event['start']}")
        print(f"    URL: {event['url'][:70]}...")
        if event.get('recurring_pattern'):
            print(f"    Recurring: {event['recurring_pattern']}")
else:
    print("❌ No 'First Friday' events found!")
    print("\nAll events found:")
    for i, event in enumerate(events[:10], 1):
        print(f"{i}. {event['title']} - {event['start']}")
    if len(events) > 10:
        print(f"... and {len(events) - 10} more")

# Also check if any events have "friday" in the title
friday_events = [e for e in events if 'friday' in e['title'].lower()]
if friday_events and not first_friday_events:
    print(f"\nFound {len(friday_events)} events with 'Friday' in title:")
    for event in friday_events[:5]:
        print(f"  - {event['title']} - {event['start']}")
