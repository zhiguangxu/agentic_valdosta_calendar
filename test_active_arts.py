#!/usr/bin/env python3
"""Test Active Arts IMPROVment class"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source

# Get Turner Center source
sources = source_manager.get_all_sources()
turner = [s for s in sources if s['type'] == 'classes' and 'turner' in s['name'].lower()][0]

print("Testing Turner Center Classes - Active Arts category...")
print("="*60)
classes = scrape_source(turner)

# Filter for Active Arts classes
active_arts = [c for c in classes if 'ACTIVE ARTS' in c['title']]

print(f"\nTotal Active Arts classes found: {len(active_arts)}")
print()

if active_arts:
    for i, cls in enumerate(active_arts, 1):
        date = cls['start'].split('T')[0]
        time = cls['start'].split('T')[1]
        print(f"{i}. {cls['title']}")
        print(f"   Date: {date} at {time}")
        if cls.get('recurring_pattern'):
            print(f"   Recurring: {cls['recurring_pattern']}")
        print()

    print("="*60)
    print(f"Expected: 2 classes (Feb 2 and Feb 9)")
    print(f"Actual: {len(active_arts)} classes")

    if len(active_arts) == 2:
        print("✅ CORRECT!")
    else:
        print("❌ WRONG! Should only be 2 classes.")
