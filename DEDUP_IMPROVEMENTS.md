# Deduplication Improvements

## Issues Fixed

### 1. "Galleries Closed" Events
**Problem**: 27 "Galleries Closed" administrative events were showing on the calendar
**Solution**: Added filter in Turner Center scraper to exclude these events

**Code Change**: `backend/generic_scraper.py` (line ~748)
```python
# Filter out "Galleries Closed" events (administrative/internal events)
if source_type == 'events' and 'galleries closed' in title.lower():
    filtered_count += 1
    continue
```

**Result**: 0 "Galleries Closed" events (reduced from 27)

### 2. Same Event with Different Titles
**Problem**: Events appearing twice on calendar:
- Feb 26: "Doo Wop Show" and "Presenter Series Second Show of the Season" (both at 7:30 PM)
- Mar 19: "Broadway Boys" and "Presenter Series Third Show of the Season" (both at 7:30 PM)

**Root Cause**: Different sources use different titles for the same event
- Turner Center: Uses descriptive series names ("Presenter Series Second Show of the Season")
- Other sources: Use show-specific names ("Doo Wop Show", "Broadway Boys")

**Solution**: Added datetime-based deduplication pass

**Code Change**: `backend/main.py` (lines 333-368)
```python
# Second pass: Deduplicate events with same date+time (even if titles differ)
datetime_dedup = {}
for event in best_events.values():
    datetime_key = event_datetime[:16]  # YYYY-MM-DDTHH:MM

    if datetime_key not in datetime_dedup:
        datetime_dedup[datetime_key] = event
    else:
        # Same date+time - likely the same event with different title
        # Prefer event with longer description
```

**Logic**:
1. First pass: Deduplicate by date + normalized title
2. Second pass: Deduplicate by date + time (catches same event with different titles)
3. Preference: Longer description > shorter description > longer title

**Result**:
- Feb 26: 1 event (kept Turner Center version with description)
- Mar 19: 1 event (kept Turner Center version with description)

## Test Results

### Before Improvements
```
Turner Center events: 33
- 27 "Galleries Closed" events included
- Duplicate shows on Feb 26 and Mar 19

Total calendar events with duplicates
```

### After Improvements
```
Turner Center events: 6 (27 galleries closed filtered out)
- "Galleries Closed": 0 events
- Feb 26: 1 event (duplicate removed)
- Mar 19: 1 event (duplicate removed)

Deduplication test:
- Input: 8 events (6 Turner + 2 from other sources)
- Output: 6 events (2 duplicates removed)
```

### Deduplication Examples
```
[DEDUP-DATETIME] Same date+time found:
  Existing: Presenter Series Second Show of the Season at 2026-02-26T19:30
  Current:  Doo Wop Show at 2026-02-26T19:30
  → Keeping existing (has description)

[DEDUP-DATETIME] Same date+time found:
  Existing: Presenter Series Third Show of the Season at 2026-03-19T19:30
  Current:  The Broadway Boys at 2026-03-19T19:30
  → Keeping existing (has description)
```

## Benefits

1. ✅ **Cleaner Calendar**: Removed 27 administrative "Galleries Closed" events
2. ✅ **No Duplicates**: Events at same date+time are merged, even with different titles
3. ✅ **Better Information**: Keeps version with longer/more detailed description
4. ✅ **Multi-Source Smart**: Works across Turner Center, Visit Valdosta, Chamber, etc.

## Technical Details

### Deduplication Strategy (2-Pass)

**Pass 1 - Title-Based**: Deduplicates events with similar titles on same date
- Normalizes titles (removes years, ordinals, articles)
- Key: `{date}_{normalized_title[:50]}`
- Handles: "2026 Annual Festival" = "Annual Festival" = "The Festival"

**Pass 2 - DateTime-Based with Smart Similarity**: Deduplicates events at exact same date+time ONLY if likely same event
- Key: `{datetime[:16]}` (YYYY-MM-DDTHH:MM)
- Only deduplicates if ANY of these conditions are true:
  - One title contains generic phrases ("Presenter Series", "Show of the Season", "Concert Series")
  - OR titles share >30% of significant words (excluding stop words)
  - OR one description mentions the other event's title
  - OR descriptions share >50% of significant words (very similar content)
- **Description parsing**: Analyzes description text to detect if events reference each other or share content
- Preserves genuinely different events that happen at the same time
- Handles: "Presenter Series Show" = "Doo Wop Show" (same time + generic title OR description overlap)

### Selection Criteria
When duplicates found, prefer:
1. Event with description over event without
2. Longer description over shorter description
3. Longer title over shorter title

This ensures Turner Center events (which typically have detailed descriptions) are preferred over brief listings from other sources.

## Bug Fix: Over-Aggressive DateTime Deduplication

### Problem Discovered
After implementing datetime deduplication, the total event count was WRONG:
- Before Turner Center: 81 events
- After Turner Center: 80 events (expected 85)
- Missing: 5 events

**Root Cause**: The datetime deduplication was removing ALL events at the same exact time, even if they were completely different events from different sources.

### Solution
Added title similarity checking before deduplicating by datetime:
1. Check if one title contains generic phrases ("Presenter Series", "Show of the Season")
2. Calculate word overlap between titles (similarity score)
3. Only deduplicate if similarity > 30% OR one title is generic
4. If different events at same time, keep BOTH using unique keys

**Result**:
- Removes duplicates like "Doo Wop" = "Presenter Series Show" ✅
- Preserves different events at same time ✅
- Correct count: 81 + 4 = 85 events ✅

## Files Changed
1. `backend/generic_scraper.py` (lines ~748-750): Filter "Galleries Closed"
2. `backend/main.py` (lines 333-408): Add smart datetime-based deduplication with similarity checking
