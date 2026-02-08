#!/usr/bin/env python3
"""Test Ceramics & Pottery classes"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from collections import Counter

# Get Turner Center source
sources = source_manager.get_all_sources()
turner = [s for s in sources if s['type'] == 'classes' and 'turner' in s['name'].lower()][0]

print("Testing Turner Center Classes - Ceramics & Pottery category...")
print("="*60)
classes = scrape_source(turner)

# Filter for Ceramics & Pottery classes
ceramics = [c for c in classes if 'CERAMICS & POTTERY' in c['title']]

print(f"\nTotal Ceramics & Pottery classes found: {len(ceramics)}")
print()

# Group by title to see unique classes
title_counts = Counter([c['title'] for c in ceramics])

print("Unique classes:")
for title, count in sorted(title_counts.items()):
    print(f"  {count}x {title}")
print()

# Show first few occurrences of each class
print("Sample occurrences:")
print()
for title in sorted(title_counts.keys()):
    occurrences = [c for c in ceramics if c['title'] == title][:3]
    print(f"{title}:")
    for c in occurrences:
        date = c['start'].split('T')[0]
        time = c['start'].split('T')[1]
        print(f"  - {date} at {time}")
        if c.get('recurring_pattern'):
            print(f"    Pattern: {c['recurring_pattern']}")
    if len(occurrences) < title_counts[title]:
        print(f"  ... and {title_counts[title] - len(occurrences)} more")
    print()
