#!/usr/bin/env python3
"""Test Turner Center classes scraping"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from datetime import datetime
import os

print("Testing Turner Center Classes...")
print("="*60)
print(f"Today's date: {datetime.now().strftime('%Y-%m-%d')}")
print("="*60)

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)

# Get Turner Center source
sources = source_manager.get_all_sources()
turner = None
for source in sources:
    if source['type'] == 'classes' and 'turner' in source['name'].lower():
        turner = source
        break

if not turner:
    print("❌ ERROR: Turner Center source not found!")
    sys.exit(1)

print(f"Found source: {turner['name']}")
print(f"URL: {turner['url']}")
print(f"Type: {turner['type']}")
print(f"Enabled: {turner['enabled']}")
print(f"Method: {turner.get('scraping_method', 'auto')}")
print()

# Scrape it
print("Scraping Turner Center classes...")
print("="*60)
classes = scrape_source(turner)

print(f"\nTotal classes found: {len(classes)}")
print()

if classes:
    print("Classes:")
    for i, cls in enumerate(classes, 1):
        class_date = cls['start'].split('T')[0] if 'T' in cls['start'] else cls['start']
        print(f"{i}. {cls['title']}")
        print(f"   Date: {class_date}")
        if 'T' in cls['start']:
            print(f"   Time: {cls['start'].split('T')[1]}")
        print(f"   URL: {cls['url'][:70]}...")
        if cls.get('recurring_pattern'):
            print(f"   Recurring: {cls['recurring_pattern']}")
        if cls.get('description'):
            desc = cls['description'][:100]
            print(f"   Description: {desc}...")
        print()

    # Check for recurring patterns
    recurring_classes = [c for c in classes if c.get('recurring_pattern')]
    print(f"\n📅 Classes with recurring patterns: {len(recurring_classes)}")
    for c in recurring_classes:
        print(f"  - {c['title']}: {c['recurring_pattern']}")

    # Check for TBD dates
    tbd_classes = [c for c in classes if 'tbd' in c['start'].lower() or 'determine' in str(c.get('description', '')).lower()]
    if tbd_classes:
        print(f"\n⚠️  Classes with TBD dates: {len(tbd_classes)}")
        for c in tbd_classes:
            print(f"  - {c['title']}: {c['start']}")
else:
    print("\n❌ No classes found!")
    print("\nPossible reasons:")
    print("1. The scraping failed (check errors above)")
    print("2. All classes are in the past and were filtered out")
    print("3. The page structure is not being parsed correctly")
