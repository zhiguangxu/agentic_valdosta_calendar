#!/usr/bin/env python3
"""Test meetings filtering for past dates"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from datetime import datetime
import os

print("Testing City of Valdosta Meetings...")
print("="*60)
print(f"Today's date: {datetime.now().strftime('%Y-%m-%d')}")
print("="*60)

# Check OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)

# Get City of Valdosta meetings source
sources = source_manager.get_all_sources()
valdosta_meetings = None
for source in sources:
    if "valdostacity.com" in source['url'] and source['type'] == 'meetings':
        valdosta_meetings = source
        break

if not valdosta_meetings:
    print("❌ ERROR: City of Valdosta meetings source not found!")
    sys.exit(1)

print(f"Found source: {valdosta_meetings['name']}")
print(f"URL: {valdosta_meetings['url']}")
print(f"Type: {valdosta_meetings['type']}")
print(f"Enabled: {valdosta_meetings['enabled']}")
print()

# Scrape it
print("Scraping City of Valdosta meetings...")
print("="*60)
meetings = scrape_source(valdosta_meetings)

print(f"\nTotal meetings found: {len(meetings)}")
print()

# Check dates
today = datetime.now().date()
past_meetings = []
future_meetings = []

for meeting in meetings:
    meeting_date = datetime.fromisoformat(meeting['start'].split('T')[0]).date()
    if meeting_date < today:
        past_meetings.append(meeting)
    else:
        future_meetings.append(meeting)

print(f"📅 Past meetings (should be FILTERED OUT): {len(past_meetings)}")
for m in past_meetings:
    print(f"  ❌ {m['title']} - {m['start']}")

print(f"\n📅 Future meetings (should be KEPT): {len(future_meetings)}")
for m in future_meetings:
    print(f"  ✅ {m['title']} - {m['start']}")

if past_meetings:
    print(f"\n⚠️  WARNING: {len(past_meetings)} past meetings are NOT being filtered!")
    print("This is a bug - past meetings should be removed.")
else:
    print(f"\n✅ SUCCESS: All meetings are in the future.")
