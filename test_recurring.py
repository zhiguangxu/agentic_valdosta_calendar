#!/usr/bin/env python3
"""Test recurring event detection"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend.generic_scraper import _expand_recurring_events
from datetime import datetime

# Test events with recurring patterns
test_events = [
    {
        'title': 'First Friday Art Walk',
        'start': '2026-02-07T19:00:00',
        'description': 'Monthly art walk',
        'url': 'http://example.com',
        'recurring_pattern': 'first friday of each month'
    },
    {
        'title': 'Chamber Meeting',
        'start': '2026-02-10T18:00:00',
        'description': 'Regular meeting',
        'url': 'http://example.com',
        'recurring_pattern': 'second saturday'
    },
    {
        'title': 'Regular Event',
        'start': '2026-03-15T14:00:00',
        'description': 'One-time event',
        'url': 'http://example.com',
        'recurring_pattern': ''
    }
]

print('Testing recurring event detection...')
print('='*60)
expanded = _expand_recurring_events(test_events)
print('='*60)
print(f'\nInput: {len(test_events)} events')
print(f'Output: {len(expanded)} events after expansion\n')

# Count how many of each type
first_friday_count = sum(1 for e in expanded if 'first friday' in e['title'].lower())
second_saturday_count = sum(1 for e in expanded if 'chamber' in e['title'].lower())
regular_count = sum(1 for e in expanded if 'regular' in e['title'].lower())

print(f'First Friday events: {first_friday_count}')
print(f'Chamber Meeting events: {second_saturday_count}')
print(f'Regular events: {regular_count}')

# Show sample dates
print('\nFirst Friday dates:')
for e in expanded:
    if 'first friday' in e['title'].lower():
        print(f"  {e['start'].split('T')[0]}")

print('\nSecond Saturday dates:')
for e in expanded:
    if 'chamber' in e['title'].lower():
        print(f"  {e['start'].split('T')[0]}")
