#!/usr/bin/env python3
"""Test the new conservative time-window deduplication"""

import sys
sys.path.insert(0, 'backend')

# Mock dependencies
from unittest.mock import Mock
sys.modules['requests'] = Mock()
sys.modules['anthropic'] = Mock()
sys.modules['openai'] = Mock()

from backend.main import deduplicate_events

# Test data with the specific duplicate cases
test_events = [
    # Feb 26 duplicates - 30 minutes apart
    {"title": "The Doo Wop Project", "start": "2026-02-26T19:00:00", "description": ""},
    {"title": "Presenter Series Second Show of the Season", "start": "2026-02-26T19:30:00",
     "description": "A Brand New Show from America's Premiere Doo Wop Group..."},

    # Mar 19 duplicates - 30 minutes apart
    {"title": "The Broadway Boys", "start": "2026-03-19T19:00:00", "description": ""},
    {"title": "Presenter Series Third Show of the Season", "start": "2026-03-19T19:30:00",
     "description": "Presenting – THE BROADWAY BOYS! The Broadway Boys is a collection..."},

    # Same day, different times, different events - should NOT be deduplicated
    {"title": "Student Recital: Tyress McGauley, jazz percussion", "start": "2026-02-26T19:00:00", "description": ""},
    {"title": "Concert Band and Wind Ensemble", "start": "2026-02-25T19:00:00", "description": ""},

    # Completely different events
    {"title": "Event A", "start": "2026-02-20T19:00:00", "description": "Description A"},
    {"title": "Event B", "start": "2026-02-21T19:00:00", "description": "Description B"},
]

print("="*80)
print("TESTING CONSERVATIVE TIME-WINDOW DEDUPLICATION")
print("="*80)

print(f"\nInput: {len(test_events)} events")
for i, e in enumerate(test_events, 1):
    print(f"  {i}. {e['title'][:50]} - {e['start']}")

print("\n" + "="*80)
print("RUNNING DEDUPLICATION...")
print("="*80 + "\n")

deduplicated = deduplicate_events(test_events)

print("\n" + "="*80)
print(f"Output: {len(deduplicated)} events")
print("="*80)

for i, e in enumerate(sorted(deduplicated, key=lambda x: x['start']), 1):
    print(f"  {i}. {e['title'][:50]} - {e['start']}")

# Verify results
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

titles = [e['title'] for e in deduplicated]

# Check Feb 26 duplicates
has_doo_wop = "The Doo Wop Project" in titles
has_presenter_2 = "Presenter Series Second Show of the Season" in titles

if has_presenter_2 and not has_doo_wop:
    print("✅ Feb 26: Kept Presenter Series, removed Doo Wop (CORRECT)")
elif has_doo_wop and not has_presenter_2:
    print("⚠️  Feb 26: Kept Doo Wop, removed Presenter Series (acceptable)")
else:
    print(f"❌ Feb 26: BOTH present or both missing! Doo Wop: {has_doo_wop}, Presenter: {has_presenter_2}")

# Check Mar 19 duplicates
has_broadway = "The Broadway Boys" in titles
has_presenter_3 = "Presenter Series Third Show of the Season" in titles

if has_presenter_3 and not has_broadway:
    print("✅ Mar 19: Kept Presenter Series, removed Broadway Boys (CORRECT)")
elif has_broadway and not has_presenter_3:
    print("⚠️  Mar 19: Kept Broadway Boys, removed Presenter Series (acceptable)")
else:
    print(f"❌ Mar 19: BOTH present or both missing! Broadway: {has_broadway}, Presenter: {has_presenter_3}")

# Check that other events are preserved
has_student_recital = any("McGauley" in t for t in titles)
has_concert_band = any("Concert Band and Wind Ensemble" in t for t in titles)
has_event_a = "Event A" in titles
has_event_b = "Event B" in titles

if has_student_recital:
    print("✅ Student Recital preserved (different event, same date)")
else:
    print("❌ Student Recital incorrectly removed")

if has_concert_band:
    print("✅ Concert Band preserved (different event, nearby date)")
else:
    print("❌ Concert Band incorrectly removed")

if has_event_a and has_event_b:
    print("✅ Event A and B preserved (completely different)")
else:
    print(f"❌ Event A/B removed - A: {has_event_a}, B: {has_event_b}")

# Expected count: 8 - 2 = 6 events
expected = 6
if len(deduplicated) == expected:
    print(f"\n✅ TOTAL COUNT CORRECT: {len(deduplicated)} events (expected {expected})")
else:
    print(f"\n⚠️  TOTAL COUNT: {len(deduplicated)} events (expected {expected})")
