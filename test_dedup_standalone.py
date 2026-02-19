#!/usr/bin/env python3
"""Standalone test for deduplication logic - no imports needed"""

import re
from typing import List, Dict

def deduplicate_events(events: List[Dict]) -> List[Dict]:
    """
    Remove duplicate events across multiple sources.
    Events are considered duplicates if they have the same date and very similar titles.
    """
    if not events:
        return []

    # Use dict to store best event for each dedup_key
    best_events = {}

    for event in events:
        # Create key from date + normalized title
        event_date = event.get('start', '').split('T')[0]  # Get date part (YYYY-MM-DD)
        event_title = event.get('title', '').lower().strip()

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

        # If we haven't seen this event before, or if this event is better, keep it
        if dedup_key not in best_events:
            best_events[dedup_key] = event
            print(f"  [DEDUP] New event: {event_title[:60]} on {event_date}")
        else:
            # Compare: prefer event with description, then longer title
            existing = best_events[dedup_key]
            existing_desc = existing.get('description', '').strip()
            current_desc = event.get('description', '').strip()

            print(f"  [DEDUP] Duplicate found:")
            print(f"    Existing: {existing.get('title', '')[:60]}")
            print(f"    Current:  {event_title[:60]}")
            print(f"    Key: {dedup_key}")

            # Prefer event with non-empty description
            if current_desc and not existing_desc:
                print(f"    → Keeping current (has description)")
                best_events[dedup_key] = event
            elif not current_desc and existing_desc:
                print(f"    → Keeping existing (has description)")
                pass  # Keep existing
            elif current_desc and existing_desc:
                # Both have descriptions - prefer longer description (more informative)
                if len(current_desc) > len(existing_desc):
                    print(f"    → Keeping current (longer description: {len(current_desc)} vs {len(existing_desc)} chars)")
                    best_events[dedup_key] = event
                else:
                    print(f"    → Keeping existing (longer or same description: {len(existing_desc)} vs {len(current_desc)} chars)")
            else:
                # Neither has description - prefer longer/more specific title
                if len(event.get('title', '')) > len(existing.get('title', '')):
                    print(f"    → Keeping current (longer title)")
                    best_events[dedup_key] = event
                else:
                    print(f"    → Keeping existing (longer or same title)")

    # Second pass: Deduplicate events with same date+time ONLY if titles suggest same event
    # This catches cases like "Presenter Series Show" vs "Doo Wop Show" at same time
    # while preserving genuinely different events that happen at the same time
    datetime_dedup = {}
    for event in best_events.values():
        event_datetime = event.get('start', '')  # Full datetime: YYYY-MM-DDTHH:MM:SS

        # Extract just date and time (ignore seconds)
        datetime_key = event_datetime[:16] if len(event_datetime) >= 16 else event_datetime

        if datetime_key not in datetime_dedup:
            datetime_dedup[datetime_key] = event
        else:
            # Same date+time found - check if they're likely the same event
            existing = datetime_dedup[datetime_key]
            existing_title = existing.get('title', '').lower()
            current_title = event.get('title', '').lower()
            existing_desc = existing.get('description', '').lower().strip()
            current_desc = event.get('description', '').lower().strip()

            # Check if one title is generic (like "Presenter Series")
            # or if titles share significant words (suggesting same event)
            is_generic_existing = any(phrase in existing_title for phrase in [
                'presenter series', 'show of the season', 'concert series'
            ])
            is_generic_current = any(phrase in current_title for phrase in [
                'presenter series', 'show of the season', 'concert series'
            ])

            # Calculate word overlap for titles (simple similarity check)
            existing_words = set(existing_title.split())
            current_words = set(current_title.split())
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'at', 'in', 'on', 'of', 'and', 'or', 'for', 'to', 'with'}
            existing_words = existing_words - stop_words
            current_words = current_words - stop_words

            if existing_words and current_words:
                overlap = len(existing_words & current_words)
                title_similarity = overlap / min(len(existing_words), len(current_words))
            else:
                title_similarity = 0

            # ALSO check description similarity - parse descriptions to find common content
            desc_similarity = 0
            desc_suggests_same = False

            if existing_desc and current_desc:
                # Check if one description mentions the other event's title
                if existing_title in current_desc or current_title in existing_desc:
                    desc_suggests_same = True

                # Check if descriptions share significant content
                existing_desc_words = set(existing_desc.split()) - stop_words
                current_desc_words = set(current_desc.split()) - stop_words

                if existing_desc_words and current_desc_words:
                    desc_overlap = len(existing_desc_words & current_desc_words)
                    desc_similarity = desc_overlap / min(len(existing_desc_words), len(current_desc_words))

                    # If descriptions are very similar (>50% overlap), likely same event
                    if desc_similarity > 0.5:
                        desc_suggests_same = True

            # Only deduplicate if evidence suggests same event
            should_deduplicate = (
                is_generic_existing or is_generic_current or  # Generic title like "Presenter Series"
                title_similarity > 0.3 or                      # Similar titles
                desc_suggests_same or                          # Descriptions suggest same event
                desc_similarity > 0.5                          # Very similar descriptions
            )

            if should_deduplicate:
                print(f"  [DEDUP-DATETIME] Same date+time found - likely duplicate:")
                print(f"    Existing: {existing.get('title', '')[:60]} at {datetime_key}")
                print(f"    Current:  {event.get('title', '')[:60]} at {datetime_key}")
                print(f"    Title similarity: {title_similarity:.2f}, Generic: {is_generic_existing or is_generic_current}")
                print(f"    Description similarity: {desc_similarity:.2f}, Desc suggests same: {desc_suggests_same}")

                # Get original description strings for comparison
                existing_desc_str = existing.get('description', '').strip()
                current_desc_str = event.get('description', '').strip()

                # Prefer event with description, then longer description
                if current_desc_str and not existing_desc_str:
                    print(f"    → Keeping current (has description)")
                    datetime_dedup[datetime_key] = event
                elif not current_desc_str and existing_desc_str:
                    print(f"    → Keeping existing (has description)")
                elif current_desc_str and existing_desc_str:
                    if len(current_desc_str) > len(existing_desc_str):
                        print(f"    → Keeping current (longer description)")
                        datetime_dedup[datetime_key] = event
                    else:
                        print(f"    → Keeping existing (longer description)")
                else:
                    # Neither has description - prefer longer title
                    if len(event.get('title', '')) > len(existing.get('title', '')):
                        print(f"    → Keeping current (longer title)")
                        datetime_dedup[datetime_key] = event
                    else:
                        print(f"    → Keeping existing")
            else:
                # Different events at same time - keep both by using unique key
                # Add event with a unique key (append counter)
                counter = 1
                unique_key = f"{datetime_key}_{counter}"
                while unique_key in datetime_dedup:
                    counter += 1
                    unique_key = f"{datetime_key}_{counter}"
                datetime_dedup[unique_key] = event
                print(f"  [DEDUP-DATETIME] Same time but different events - keeping both:")
                print(f"    Event 1: {existing.get('title', '')[:60]}")
                print(f"    Event 2: {event.get('title', '')[:60]}")

    return list(datetime_dedup.values())


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

# Expected total
expected = 2  # 1 event for Feb 26, 1 event for Mar 19
if len(deduplicated) == expected:
    print(f"\n✅ TOTAL COUNT CORRECT: {len(deduplicated)} events (expected {expected})")
else:
    print(f"\n❌ TOTAL COUNT WRONG: {len(deduplicated)} events (expected {expected})")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
