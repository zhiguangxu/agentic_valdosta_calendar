#!/usr/bin/env python3
"""Test the improved datetime deduplication logic"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend')

from main import deduplicate_events

# Test data: simulating the user's scenario
test_events = [
    # Original events from 4 sources (before Turner Center)
    {"title": "Event A", "start": "2026-02-20T19:00:00", "description": "Description A"},
    {"title": "Event B", "start": "2026-02-21T19:00:00", "description": "Description B"},
    {"title": "Event C", "start": "2026-02-22T19:00:00", "description": "Description C"},
    {"title": "Event D", "start": "2026-02-23T19:00:00", "description": "Description D"},
    {"title": "Event E", "start": "2026-02-24T19:00:00", "description": "Description E"},

    # Turner Center events - some duplicates, some unique
    # Feb 26: Duplicate with different name (should be deduplicated)
    {"title": "Presenter Series Second Show of the Season", "start": "2026-02-26T19:30:00", "description": "Join us for an evening of..."},
    {"title": "Doo Wop Show", "start": "2026-02-26T19:30:00", "description": ""},

    # Mar 19: Duplicate with different name (should be deduplicated)
    {"title": "Presenter Series Third Show of the Season", "start": "2026-03-19T19:30:00", "description": "Broadway Boys perform classic..."},
    {"title": "The Broadway Boys", "start": "2026-03-19T19:30:00", "description": ""},

    # Unique Turner events (should be kept)
    {"title": "Turner Event 1", "start": "2026-02-18T18:00:00", "description": "Unique Turner event"},
    {"title": "Turner Event 2", "start": "2026-02-22T15:00:00", "description": "Another unique Turner event"},
    {"title": "Turner Event 3", "start": "2026-03-16T20:00:00", "description": "Yet another Turner event"},
    {"title": "Turner Event 4", "start": "2026-03-20T19:00:00", "description": "Fourth unique Turner event"},
]

print(f"Total events before deduplication: {len(test_events)}")
print("\nRunning deduplication...")
print("=" * 80)

deduplicated = deduplicate_events(test_events)

print("=" * 80)
print(f"\nTotal events after deduplication: {len(deduplicated)}")
print(f"Expected: 11 events (5 original + 4 unique Turner + 2 deduplicated into 2)")
print(f"Actual: {len(deduplicated)} events")

print("\nFinal events:")
for i, event in enumerate(sorted(deduplicated, key=lambda x: x['start']), 1):
    print(f"{i}. {event['title'][:50]} - {event['start']}")

# Check results
if len(deduplicated) == 11:
    print("\n✅ PASS: Correct number of events!")
else:
    print(f"\n❌ FAIL: Expected 11 events, got {len(deduplicated)}")

# Check specific duplicates were removed
titles = [e['title'] for e in deduplicated]
has_doo_wop = "Doo Wop Show" in titles
has_broadway = "The Broadway Boys" in titles
has_presenter_2 = "Presenter Series Second Show of the Season" in titles
has_presenter_3 = "Presenter Series Third Show of the Season" in titles

print("\nDuplicate check:")
if has_presenter_2 and not has_doo_wop:
    print("✅ Feb 26: Kept Presenter Series, removed Doo Wop")
elif has_doo_wop and not has_presenter_2:
    print("✅ Feb 26: Kept Doo Wop, removed Presenter Series")
else:
    print(f"❌ Feb 26: Both present or both missing (Doo Wop: {has_doo_wop}, Presenter: {has_presenter_2})")

if has_presenter_3 and not has_broadway:
    print("✅ Mar 19: Kept Presenter Series, removed Broadway Boys")
elif has_broadway and not has_presenter_3:
    print("✅ Mar 19: Kept Broadway Boys, removed Presenter Series")
else:
    print(f"❌ Mar 19: Both present or both missing (Broadway: {has_broadway}, Presenter: {has_presenter_3})")
