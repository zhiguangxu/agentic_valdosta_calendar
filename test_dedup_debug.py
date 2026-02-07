#!/usr/bin/env python3
"""Debug deduplication keys"""

import sys
import re
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

# Test the normalization logic
titles = [
    '2026 Annual Spring Festival',
    'Spring Festival',
    'Annual Spring Festival'
]

for title in titles:
    event_date = '2026-03-15'
    event_title = title.lower().strip()

    # Normalize title for comparison
    normalized = event_title

    # Remove year prefixes like "2026" FIRST (before annual)
    normalized = re.sub(r'^20\d{2}\s+', '', normalized)

    # Remove ordinal indicators (1st, 2nd, 3rd, 4th, etc.) with "annual"
    normalized = re.sub(r'^\d+(st|nd|rd|th)\s+annual\s+', '', normalized, flags=re.IGNORECASE)

    # Remove standalone "annual" at beginning
    normalized = re.sub(r'^annual\s+', '', normalized, flags=re.IGNORECASE)

    # Remove common prefixes
    for prefix in ['the ', 'a ', 'an ']:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    # Remove special characters for comparison
    normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
    normalized = ' '.join(normalized.split())  # Normalize whitespace

    # Create deduplication key
    dedup_key = f"{event_date}_{normalized[:50]}"  # First 50 chars of normalized title

    print(f"Title: '{title}'")
    print(f"  → Normalized: '{normalized}'")
    print(f"  → Key: '{dedup_key}'")
    print()
