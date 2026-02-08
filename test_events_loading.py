#!/usr/bin/env python3
"""Test events loading"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from backend import generic_scraper
import os

print("Testing events loading...")
print("="*60)

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    print("   Set it with: export OPENAI_API_KEY='your-key'")
    sys.exit(1)
else:
    print(f"✅ OpenAI API key is set (length: {len(api_key)})")

# Load event sources
print("\nLoading event sources...")
event_sources = source_manager.get_sources_by_type('events')
print(f"Found {len(event_sources)} event sources:")
for source in event_sources:
    status = "✅ ENABLED" if source['enabled'] else "❌ DISABLED"
    print(f"  {status} - {source['name']}")
    print(f"    URL: {source['url']}")
    print(f"    Method: {source.get('scraping_method', 'auto')}")

# Try scraping the first enabled source
enabled_sources = [s for s in event_sources if s['enabled']]
if not enabled_sources:
    print("\n❌ ERROR: No enabled event sources found!")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"Testing scraping: {enabled_sources[0]['name']}")
print(f"{'='*60}")

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # Test scraping
    print("Starting scrape...")
    events = scrape_source(enabled_sources[0])

    print(f"\n{'='*60}")
    print(f"RESULT: Found {len(events)} events")
    print(f"{'='*60}")

    if events:
        print("\nFirst 3 events:")
        for i, event in enumerate(events[:3], 1):
            print(f"{i}. {event['title']}")
            print(f"   Date: {event['start']}")
            print(f"   URL: {event['url'][:60]}...")
    else:
        print("\n❌ No events found!")
        print("   This might indicate a scraping issue.")

except Exception as e:
    print(f"\n❌ ERROR during scraping: {e}")
    import traceback
    traceback.print_exc()
