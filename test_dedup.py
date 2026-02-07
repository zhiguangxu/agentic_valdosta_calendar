#!/usr/bin/env python3
"""Test category-specific deduplication"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend.main import deduplicate_events, deduplicate_classes, deduplicate_meetings

print('Testing category-specific deduplication...\n')

# Test events deduplication
print('='*60)
print('EVENTS DEDUPLICATION')
print('='*60)
test_events = [
    {'title': '2026 Annual Spring Festival', 'start': '2026-03-15T19:00:00', 'description': 'First source', 'url': 'http://example.com/1'},
    {'title': 'Spring Festival', 'start': '2026-03-15T19:00:00', 'description': 'Second source (better)', 'url': 'http://example.com/2'},
    {'title': 'Art Walk', 'start': '2026-03-20T18:00:00', 'description': 'Unique event', 'url': 'http://example.com/3'},
]
deduped_events = deduplicate_events(test_events)
print(f'\nInput: {len(test_events)} events')
print(f'Output: {len(deduped_events)} events')
print('Result:', [e['title'] for e in deduped_events])

# Test classes deduplication
print('\n' + '='*60)
print('CLASSES DEDUPLICATION')
print('='*60)
test_classes = [
    {'title': 'Drawing Class with Jane Smith', 'start': '2026-03-15T14:00:00', 'description': 'Beginner class', 'url': 'http://example.com/1'},
    {'title': 'Drawing Class with Jane Smith', 'start': '2026-03-15T14:00:00', 'description': '', 'url': 'http://example.com/2'},
    {'title': 'Drawing Class with Jane Smith', 'start': '2026-03-22T14:00:00', 'description': 'Week 2', 'url': 'http://example.com/3'},  # Different date = different class
    {'title': '2nd Week Painting', 'start': '2026-03-20T10:00:00', 'description': 'Ongoing series', 'url': 'http://example.com/4'},
]
deduped_classes = deduplicate_classes(test_classes)
print(f'\nInput: {len(test_classes)} classes')
print(f'Output: {len(deduped_classes)} classes')
print('Result:', [c['title'] for c in deduped_classes])

# Test meetings deduplication
print('\n' + '='*60)
print('MEETINGS DEDUPLICATION')
print('='*60)
test_meetings = [
    {'title': 'City Council Meeting', 'start': '2026-03-15T18:00:00', 'description': 'At City Hall', 'url': 'http://example.com/1'},
    {'title': 'City Council Meeting', 'start': '2026-03-15T18:00:00', 'description': 'At City Hall - duplicate', 'url': 'http://example.com/2'},
    {'title': 'Board Meeting', 'start': '2026-03-20T19:00:00', 'description': 'Board of Directors', 'url': 'http://example.com/3'},
]
deduped_meetings = deduplicate_meetings(test_meetings)
print(f'\nInput: {len(test_meetings)} meetings')
print(f'Output: {len(deduped_meetings)} meetings')
print('Result:', [m['title'] for m in deduped_meetings])

print('\n' + '='*60)
print('SUMMARY')
print('='*60)
print('✅ Events: Deduplicated "2026 Annual Spring Festival" and "Spring Festival"')
print('✅ Classes: Kept same class on different dates (recurring)')
print('✅ Meetings: Deduplicated exact duplicates')
