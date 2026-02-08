#!/usr/bin/env python3
"""Test Turner Center classes - summarized output"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from datetime import datetime
from collections import Counter

# Get Turner Center source
sources = source_manager.get_all_sources()
turner = [s for s in sources if s['type'] == 'classes' and 'turner' in s['name'].lower()][0]

print("Testing Turner Center Classes...")
print("="*60)
classes = scrape_source(turner)

print(f"\nTotal classes found: {len(classes)}")

# Group by title
title_counts = Counter([c['title'] for c in classes])

print(f"\nUnique class titles: {len(title_counts)}")
for title, count in sorted(title_counts.items(), key=lambda x: -x[1]):
    print(f"  {count}x {title}")

# Show first 3 occurrences of one class
if classes:
    sample_title = classes[0]['title']
    sample_classes = [c for c in classes if c['title'] == sample_title][:3]
    print(f"\nFirst 3 occurrences of '{sample_title}':")
    for c in sample_classes:
        date = c['start'].split('T')[0]
        time = c['start'].split('T')[1]
        print(f"  - {date} at {time}")
