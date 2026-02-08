#!/usr/bin/env python3
"""Test all Turner Center class categories"""

import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

from backend import source_manager
from backend.main import scrape_source
from collections import defaultdict

# Get Turner Center source
sources = source_manager.get_all_sources()
turner = [s for s in sources if s['type'] == 'classes' and 'turner' in s['name'].lower()][0]

print("Testing ALL Turner Center Classes...")
print("="*60)
classes = scrape_source(turner)

print(f"\nTotal classes found: {len(classes)}")
print()

# Group by category
by_category = defaultdict(list)
for cls in classes:
    # Extract category from title (before the colon)
    if ':' in cls['title']:
        category = cls['title'].split(':')[0].strip()
        class_name = cls['title'].split(':', 1)[1].strip()
        by_category[category].append((class_name, cls['start']))

# Show results by category
categories = sorted(by_category.keys())

print("EXTRACTION RESULTS BY CATEGORY:")
print("="*60)

for category in categories:
    classes_list = by_category[category]
    unique_classes = set(c[0] for c in classes_list)

    print(f"\n{category}:")
    print(f"  Unique classes extracted: {len(unique_classes)}")

    # Group by class name to show dates
    by_name = defaultdict(list)
    for name, date in classes_list:
        by_name[name].append(date)

    for name in sorted(unique_classes):
        dates = sorted(by_name[name])
        print(f"    • {name}")
        print(f"      Dates: {len(dates)} occurrence(s)")
        if len(dates) <= 3:
            for d in dates:
                print(f"        - {d}")
        else:
            for d in dates[:2]:
                print(f"        - {d}")
            print(f"        ... and {len(dates) - 2} more")

print("\n" + "="*60)
print(f"SUMMARY: {len(classes)} total class occurrences across {len(categories)} categories")
