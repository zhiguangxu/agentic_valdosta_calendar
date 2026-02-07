"""Test if Presenter Series events will be deduplicated"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.main import deduplicate_events

# Simulate events from both sources
visit_valdosta_event = {
    'title': 'The Doo Wop Project',
    'start': '2026-02-26T19:30:00',
    'description': 'The Doo Wop Project performance...',
    'url': 'https://example.com/doo-wop'
}

turner_center_event = {
    'title': 'PRESENTER SERIES',
    'start': '2026-02-26T19:00:00',
    'description': 'Presenter Series featuring nationally touring shows...',
    'url': 'https://turnercenter.org/presenter-series/'
}

# These are different events (different titles, different venues)
events = [visit_valdosta_event, turner_center_event]

print("Before deduplication:")
for e in events:
    print(f"  - {e['title']} on {e['start']}")

deduplicated = deduplicate_events(events)

print(f"\nAfter deduplication: {len(deduplicated)} event(s)")
for e in deduplicated:
    print(f"  - {e['title']} on {e['start']}")

print("\n" + "="*80)
print("Analysis: These should NOT be deduplicated because:")
print("  - Different titles: 'The Doo Wop Project' vs 'PRESENTER SERIES'")
print("  - Different times: 19:30 vs 19:00")
print("  - They are separate events on the same night")
