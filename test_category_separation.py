"""Test category separation - ensure Events and Classes don't interfere"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend import source_manager

print("="*80)
print("TESTING CATEGORY SEPARATION")
print("="*80)

# Test 1: Check sources by type
print("\n1. Sources by type:")
events_sources = source_manager.get_sources_by_type('events')
classes_sources = source_manager.get_sources_by_type('classes')
meetings_sources = source_manager.get_sources_by_type('meetings')

print(f"\nEvents sources ({len(events_sources)}):")
for s in events_sources:
    print(f"  - ID {s['id']}: {s['name']} ({s['url']})")

print(f"\nClasses sources ({len(classes_sources)}):")
for s in classes_sources:
    print(f"  - ID {s['id']}: {s['name']} ({s['url']})")

print(f"\nMeetings sources ({len(meetings_sources)}):")
for s in meetings_sources:
    print(f"  - ID {s['id']}: {s['name']} ({s['url']})")

# Test 2: Verify no overlap
print("\n2. Checking for overlap:")
events_ids = set(s['id'] for s in events_sources)
classes_ids = set(s['id'] for s in classes_sources)
meetings_ids = set(s['id'] for s in meetings_sources)

overlap_events_classes = events_ids & classes_ids
overlap_events_meetings = events_ids & meetings_ids
overlap_classes_meetings = classes_ids & meetings_ids

if overlap_events_classes:
    print(f"  ⚠️  WARNING: Events and Classes share sources: {overlap_events_classes}")
else:
    print("  ✅ No overlap between Events and Classes")

if overlap_events_meetings:
    print(f"  ⚠️  WARNING: Events and Meetings share sources: {overlap_events_meetings}")
else:
    print("  ✅ No overlap between Events and Meetings")

if overlap_classes_meetings:
    print(f"  ⚠️  WARNING: Classes and Meetings share sources: {overlap_classes_meetings}")
else:
    print("  ✅ No overlap between Classes and Meetings")

print("\n" + "="*80)
print("CATEGORY SEPARATION TEST COMPLETE")
print("="*80)
