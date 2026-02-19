# Deduplication Bug Fix - February 18, 2026

## Problem
After adding Turner Center as an events source, the deduplication logic was **removing valid events**:
- **Before Turner Center**: 81 events from 4 sources
- **After Turner Center**: 80 events (WRONG - decreased by 1!)
- **Expected**: 85 events (81 + 4 unique Turner events)
- **Missing**: 5 events

Additionally, duplicates were still showing:
- Feb 26: "Doo Wop Show" showing twice
- Mar 19: "Broadway Boys" showing twice

## Root Cause
The datetime deduplication pass was **too aggressive**. It removed ALL events at the exact same date+time, even if they were completely different events from different sources.

Example:
- Event A from Visit Valdosta at 7:00 PM
- Event B from Chamber of Commerce at 7:00 PM
- Turner Event C at 7:00 PM

The old logic would keep only ONE of these three events, even though they're all different!

## The Fix
Modified `/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend/main.py` (lines 333-408)

Added **smart title similarity checking** before deduplicating by datetime:

### Deduplication Logic (Enhanced with Description Parsing)
```python
# Only deduplicate events at same time if ANY of these are true:

1. One title contains generic phrases:
   - "Presenter Series"
   - "Show of the Season"
   - "Concert Series"

2. OR titles share >30% of significant words (excluding stop words like "the", "a", "and")

3. OR one description mentions the other event's title
   - Example: "Doo Wop Show" description mentions "Presenter Series"

4. OR descriptions share >50% of significant words
   - Descriptions have very similar content → likely same event

5. If NONE of above conditions met:
   - Keep BOTH events by using unique keys
   - Don't remove either one
```

### What This Achieves
✅ **Removes intended duplicates**:
- "Doo Wop Show" + "Presenter Series Second Show" → Keep 1 (generic title detected)
- "Broadway Boys" + "Presenter Series Third Show" → Keep 1 (generic title detected)

✅ **Preserves different events at same time**:
- "Workshop A" at 7:00 PM + "Concert B" at 7:00 PM → Keep BOTH (different titles, low similarity)

## How to Test

1. **Restart the backend server** to apply changes:
   ```bash
   cd /Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend
   # Stop current backend if running
   # Start backend: python main.py
   ```

2. **Check the calendar UI**:
   - Total events should be **85** (not 80)
   - Feb 26: Should show **1 event** (not 2)
   - Mar 19: Should show **1 event** (not 2)

3. **Verify Turner Center added 4 events**:
   - Feb 18: Turner event
   - Feb 22: Turner event
   - Mar 16: Turner event
   - Mar 20: Turner event

## Expected Results

### Event Count
| Source | Count |
|--------|-------|
| Visit Valdosta | ~25 |
| Valdosta City | ~15 |
| Chamber of Commerce | ~20 |
| VSU Concert Calendar | ~21 |
| Turner Center (events) | 4 unique |
| **Total** | **85** |

### Deduplication Log
When backend runs, you should see logs like:
```
[DEDUP-DATETIME] Same date+time found - likely duplicate:
  Existing: Presenter Series Second Show of the Season at 2026-02-26T19:30
  Current:  Doo Wop Show at 2026-02-26T19:30
  Similarity: 0.00, Generic: True
  → Keeping existing (has description)

[DEDUP-DATETIME] Same time but different events - keeping both:
  Event 1: Workshop on Art
  Event 2: Jazz Concert
```

## Technical Details

### Files Modified
- `backend/main.py`: Lines 333-408 (deduplicate_events function)

### Key Changes
1. Added title similarity calculation using word overlap
2. Added generic phrase detection
3. Only deduplicate if similarity > 0.3 OR generic phrase found
4. Use unique keys to preserve different events at same time

### Similarity Calculation
```python
# Remove stop words: 'the', 'a', 'an', 'at', 'in', 'on', 'of', 'and', 'or', 'for', 'to', 'with'
# Calculate overlap: common words / min(words in title1, words in title2)
# Example:
#   "Art Workshop" vs "Painting Workshop" → 1/2 = 0.5 similarity (DEDUPE)
#   "Art Workshop" vs "Jazz Concert" → 0/2 = 0.0 similarity (KEEP BOTH)
```

## Verification Checklist

- [ ] Backend server restarted
- [ ] Total events = 85 (was 80)
- [ ] Feb 26: 1 event showing (was 2)
- [ ] Mar 19: 1 event showing (was 2)
- [ ] Turner Center added 4 events
- [ ] No valid events missing from calendar

## Rollback (if needed)
If this fix causes issues, revert `backend/main.py` lines 333-408 to the previous version (datetime deduplication without similarity checking).

However, note that the previous version had the bug of removing valid events!
