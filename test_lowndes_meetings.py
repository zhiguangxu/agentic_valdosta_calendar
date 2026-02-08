#!/usr/bin/env python3
"""Test Lowndes County Board of Commissioners meetings"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from datetime import datetime
import os

print("Testing Lowndes County Board of Commissioners Meetings...")
print("="*60)
print(f"Today's date: {datetime.now().strftime('%Y-%m-%d')}")
print("="*60)

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)

# Get Lowndes County source
sources = source_manager.get_all_sources()
lowndes = None
for source in sources:
    if "lowndes" in source['name'].lower() and source['type'] == 'meetings':
        lowndes = source
        break

if not lowndes:
    print("❌ ERROR: Lowndes County source not found!")
    sys.exit(1)

print(f"Found source: {lowndes['name']}")
print(f"URL: {lowndes['url']}")
print(f"Type: {lowndes['type']}")
print(f"Enabled: {lowndes['enabled']}")
print(f"Method: {lowndes.get('scraping_method', 'auto')}")
print()

# Scrape it
print("Scraping Lowndes County meetings...")
print("="*60)
meetings = scrape_source(lowndes)

print(f"\nTotal meetings found: {len(meetings)}")

if meetings:
    print("\nMeetings:")
    for i, meeting in enumerate(meetings, 1):
        meeting_date = meeting['start'].split('T')[0]
        print(f"{i}. {meeting['title']}")
        print(f"   Date: {meeting_date}")
        print(f"   Time: {meeting['start'].split('T')[1]}")
        print(f"   URL: {meeting['url'][:70]}...")
        if meeting.get('recurring_pattern'):
            print(f"   Recurring: {meeting['recurring_pattern']}")
        print()
else:
    print("\n❌ No meetings found!")
    print("\nPossible reasons:")
    print("1. The scraping failed (check errors above)")
    print("2. All meetings are in the past and were filtered out")
    print("3. The calendar page has no events")
    print("4. The page structure is not being parsed correctly")
