#!/usr/bin/env python3
"""Test deduplication for the specific Feb 26 and Mar 19 duplicates"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Mock the imports that require external dependencies
import sys
from unittest.mock import Mock
sys.modules['requests'] = Mock()
sys.modules['anthropic'] = Mock()
sys.modules['openai'] = Mock()

# Now import the deduplication function
from backend.main import deduplicate_events

# Test data matching the actual events from the sources
test_events = [
    # From Visit Valdosta - Feb 26
    {
        "title": "The Doo Wop Project",
        "start": "2026-02-26T19:30:00",
        "description": ""
    },
    # From Turner Center - Feb 26 (same event, different title)
    {
        "title": "Presenter Series Second Show of the Season",
        "start": "2026-02-26T19:30:00",
        "description": "Join us for an unforgettable evening of music..."
    },
    # From Visit Valdosta - Mar 19
    {
        "title": "The Broadway Boys",
        "start": "2026-03-19T19:30:00",
        "description": ""
    },
    # From Turner Center - Mar 19 (same event, different title)
    {
        "title": "Presenter Series Third Show of the Season",
        "start": "2026-03-19T19:30:00",
        "description": "Experience the magic of Broadway..."
    },
    # Some other events that should NOT be deduplicated
    {
        "title": "Workshop A",
        "start": "2026-02-26T19:30:00",  # Same time as Doo Wop
        "description": "Art workshop for beginners"
    },
    {
        "title": "Event X",
        "start": "2026-03-20T19:00:00",
        "description": "Different event"
    }
]

print("="*80)
print("TESTING DEDUPLICATION FOR FEB 26 AND MAR 19 DUPLICATES")
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

# Check results
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

titles = [e['title'] for e in deduplicated]

# Feb 26 check
has_doo_wop = "The Doo Wop Project" in titles
has_presenter_2 = "Presenter Series Second Show of the Season" in titles
has_workshop = "Workshop A" in titles

if (has_presenter_2 and not has_doo_wop) or (has_doo_wop and not has_presenter_2):
    print("✅ Feb 26: Duplicate removed (kept only one of Doo Wop / Presenter Series)")
else:
    print(f"❌ Feb 26: BOTH duplicates present! Doo Wop: {has_doo_wop}, Presenter: {has_presenter_2}")

# Mar 19 check
has_broadway = "The Broadway Boys" in titles
has_presenter_3 = "Presenter Series Third Show of the Season" in titles

if (has_presenter_3 and not has_broadway) or (has_broadway and not has_presenter_3):
    print("✅ Mar 19: Duplicate removed (kept only one of Broadway Boys / Presenter Series)")
else:
    print(f"❌ Mar 19: BOTH duplicates present! Broadway: {has_broadway}, Presenter: {has_presenter_3}")

# Workshop check - should be kept even though same time as Doo Wop/Presenter
if not has_workshop:
    print("❌ Workshop A: INCORRECTLY REMOVED (should be kept - different event at same time)")
else:
    print("✅ Workshop A: Correctly kept (different event at same time)")

# Expected total
expected = 4  # Doo Wop OR Presenter 2, Broadway OR Presenter 3, Workshop A, Event X
if len(deduplicated) == expected:
    print(f"\n✅ TOTAL COUNT CORRECT: {len(deduplicated)} events (expected {expected})")
else:
    print(f"\n❌ TOTAL COUNT WRONG: {len(deduplicated)} events (expected {expected})")
