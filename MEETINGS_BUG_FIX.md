# Meetings Bug Fix - Incorrect Expansion

## Problem
Lowndes County meetings were showing **incorrect and inconsistent results**:
- Expected: 6 meetings (2 in Feb, 4 in Mar) matching the website
- Actual: 30 meetings (5x expansion due to incorrect recurring pattern detection)

## Root Cause
The scraper was:
1. Correctly extracting 6 meetings from the website with specific dates
2. The AI was identifying them as "Third Tuesday monthly recurring" pattern (incorrectly)
3. The `_expand_recurring_events()` function was expanding each meeting into 5 additional occurrences
4. Result: 6 meetings × 5 expansions = 30 meetings

**Why the pattern detection was wrong:**
- The actual meeting dates were: Feb 23 (Mon), Feb 24 (Tue), Mar 9 (Mon), Mar 10 (Tue), Mar 23 (Mon), Mar 24 (Tue)
- These are NOT on the "third Tuesday" of each month
- They occur on different weeks throughout the months
- The AI was incorrectly generalizing a pattern from these specific dates

## The Fix
Modified `backend/generic_scraper.py` line 1449:

**Before:**
```python
def _expand_recurring_events(results: List[Dict], source_type: str = "events") -> List[Dict]:
    """Detect and expand recurring events into multiple occurrences

    IMPORTANT: Classes are NEVER expanded - they should provide specific dates only.
    Only events and meetings use recurring pattern expansion.
    """
    # SAFEGUARD: Never expand classes, even if AI accidentally sets recurring_pattern
    if source_type == 'classes':
        print(f"  [RECURRING] Skipping expansion for classes...")
        return results
```

**After:**
```python
def _expand_recurring_events(results: List[Dict], source_type: str = "events") -> List[Dict]:
    """Detect and expand recurring events into multiple occurrences

    IMPORTANT: Classes and meetings are NEVER expanded - they should provide specific dates only.
    Only events use recurring pattern expansion.
    """
    # SAFEGUARD: Never expand classes or meetings, even if AI accidentally sets recurring_pattern
    # Meetings are scheduled with specific dates on their websites and should be displayed as-is
    if source_type in ['classes', 'meetings']:
        print(f"  [RECURRING] Skipping expansion for {source_type}...")
        return results
```

**Rationale:**
- Meetings are scheduled with **specific dates** on their source websites
- We should display exactly what the website shows, not generate additional meetings
- Unlike community events (concerts, festivals) which may have true recurring patterns, meetings are typically scheduled individually
- The website already provides all scheduled meeting dates through the date range query

## Additional Changes
Updated the `_generate_meetings_prompt()` to emphasize extracting only specific dates:
- Instruction 7: "Extract ONLY the specific meeting dates shown on the page - do NOT infer or generate recurring patterns"
- This helps prevent the AI from adding misleading recurring_pattern metadata

## Testing
```bash
uv run python test_lowndes_meetings.py
```

**Result:**
- ✅ Correctly shows 6 meetings
- ✅ 2 meetings in February (Feb 23, 24)
- ✅ 4 meetings in March (Mar 9, 10, 23, 24)
- ✅ No incorrect expansion

## Files Changed
- `backend/generic_scraper.py` (line 1449-1462): Added meetings to expansion skip list
- `backend/generic_scraper.py` (line 397-425): Updated meetings prompt to prevent recurring pattern inference

## Impact
- **Lowndes County meetings**: Now shows correct 6 meetings instead of 30
- **City of Valdosta meetings**: Also benefits from this fix
- **Events and Classes**: Unaffected (events still expand recurring patterns, classes still skip expansion)

## Deployment
After fixing, deploy to Hugging Face:
```bash
cd frontend
npm run build
cp -r build/* ../backend/static/
cd ..
git add -A
git commit -m "Fix meetings: Disable recurring pattern expansion"
git push hf_origin master:main
```
