# Turner Center Events Implementation

## Overview
Added Turner Center for the Arts as an events source, scraping concerts, gallery events, community events, and workshops - **excluding classes** (which are handled separately).

## Implementation

### 1. API-Based Scraping
Modified `backend/generic_scraper.py` to handle Turner Center events:

**Function**: `_scrape_turner_center_api()`
- Fetches all events from The Events Calendar API
- For events: Filters out items in the "Classes" category
- For classes: Uses category filter in API
- Supports pagination (fetches all pages)
- Decodes HTML entities properly

### 2. Category Filtering
Turner Center event categories:
- ✅ **Concerts** (included)
- ✅ **Gallery Events** (included)
- ✅ **Community Event** (included)
- ✅ **Workshops** (included)
- ✅ **Holidays & General Closures** (included)
- ❌ **Classes** (excluded - handled by separate classes source)

### 3. Deduplication Improvements
Enhanced `backend/main.py` deduplication for events:

**Previous Logic:**
- When both events had descriptions → preferred longer **title**
- Problem: Kept events with year prefixes even if description was worse

**New Logic:**
```python
elif current_desc and existing_desc:
    # Both have descriptions - prefer longer description (more informative)
    if len(current_desc) > len(existing_desc):
        best_events[dedup_key] = event  # Keep event with better description
```

**Benefits:**
- Keeps most informative event when duplicates exist across sources
- Turner Center often has detailed descriptions → will be preferred
- Prevents keeping events just because they have "2026" prefix in title

## Test Results

### Events Scraped
```
Turner Center API: 122 total items
- 89 classes filtered out
- 33 events extracted
```

### Sample Events
- Artist Talk
- GALLERIES CLOSED FOR ART CHANGEOUT
- New Exhibit Opening Reception
- Presenter Series Second Show of the Season
- 6th Annual Art of Writing Contest Awards Reception
- Concert performances
- Gallery openings

### Deduplication Test
```
Before deduplication: 35 events (Turner + other sources)
After deduplication: 34 events
Duplicates removed: 1 (Artist Talk appeared in multiple sources)
```

### Description Priority Test
```
Input: Same event from 3 sources
- Turner Center: Full description (78 chars)
- Visit Valdosta: No description
- Chamber: Short description (10 chars)

Result: Kept Turner Center event (longest description)
```

## Files Changed

### 1. `backend/generic_scraper.py`
- **Lines 677-791**: Enhanced `_scrape_turner_center_api()` to handle both classes and events
- **Line 809**: Updated detection to handle both `source_type='classes'` and `source_type='events'`

### 2. `backend/main.py`
- **Lines 311-324**: Improved `deduplicate_events()` to prioritize longer descriptions

### 3. `backend/sources.json`
- Turner Center already added as events source (ID: 9) via Settings UI

## Source Configuration
```json
{
  "id": "9",
  "name": "Turner Center for the Arts",
  "url": "https://turnercenter.org/events/",
  "type": "events",
  "enabled": true,
  "scraping_method": "ai_twostage"
}
```

## Benefits

1. ✅ **Comprehensive Coverage**: All Turner Center events (not just classes)
2. ✅ **No Duplicates**: Classes are scraped separately, events exclude classes
3. ✅ **Smart Deduplication**: Keeps most informative event across sources
4. ✅ **Reliable**: API-based scraping (no HTML parsing issues)
5. ✅ **Complete**: Pagination ensures all events are fetched

## Categories Breakdown
From Turner Center API response:
- **Events**: 33 items (concerts, gallery events, community events)
- **Classes**: 89 items (handled by separate classes source)
- **Total**: 122 items

## Integration with Other Sources
Turner Center events are deduplicated with:
- Visit Valdosta events
- Valdosta City calendar events
- Chamber of Commerce events
- VSU Concert calendar events

The improved deduplication ensures the best version of each event is displayed on the calendar.
