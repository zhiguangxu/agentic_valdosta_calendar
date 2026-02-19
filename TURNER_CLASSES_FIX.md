# Turner Center Classes Fix

## Problem
Turner Center website (https://turnercenter.org/events/) displays both events and classes on the same calendar, with classes marked in red. The previous scraper was:
1. Extracting all events (not just classes)
2. Unable to reliably filter classes from the HTML
3. The page loads content dynamically via JavaScript

## Investigation
1. **Calendar Structure**: The site uses The Events Calendar WordPress plugin
2. **Category Markers**: Classes have CSS classes `cat_classes` and `tribe_events_cat-classes`
3. **Dynamic Loading**: Events are loaded via JavaScript, making HTML scraping unreliable
4. **REST API**: The Events Calendar plugin provides a REST API at `/wp-json/tribe/events/v1/events`

## Solution
Implemented API-based scraping using The Events Calendar REST API:

### API Endpoint
```
https://turnercenter.org/wp-json/tribe/events/v1/events
```

### Parameters
- `per_page`: 100 (maximum results per page)
- `page`: Page number for pagination
- `start_date`: Today's date (YYYY-MM-DD)
- `end_date`: 6 months from today (YYYY-MM-DD)
- `categories`: "classes" (filters to only classes)

### Implementation Details
1. **Function**: Added `_scrape_turner_center_api()` in `generic_scraper.py`
2. **Pagination**: Automatically fetches all pages of results
3. **HTML Decoding**: Uses `html.unescape()` to decode entities (& ,—, etc.)
4. **Date Parsing**: Converts API date format to ISO format for calendar display

## Code Changes

### File: `backend/generic_scraper.py`

#### 1. Added Special Detection (line ~686)
```python
# SPECIAL HANDLING: Turner Center uses a REST API for events
if 'turnercenter.org' in url and source_type == 'classes':
    print(f"[Two-Stage] Detected Turner Center classes, using REST API")
    return _scrape_turner_center_api(url, source_type)
```

#### 2. Added New Function (line ~677)
```python
def _scrape_turner_center_api(url: str, source_type: str = "classes") -> List[Dict]:
    """
    Scrape Turner Center classes using their REST API.
    Handles pagination and HTML entity decoding.
    """
    # Implementation details...
```

## Test Results

### Command
```bash
uv run python -c "..." # Test Turner API scraping
```

### Output
```
[Turner API] Page 1: Received 50 classes
[Turner API] Page 2: Received 39 classes
[Turner API] Total processed: 89 classes
```

### Results by Month
- **February 2026**: 18 classes
- **March 2026**: 53 classes
- **April 2026**: 18 classes
- **Total**: 89 classes

### Sample Classes
- Weekday Pottery Class
- Comic & Manga Illustration Class
- The Hal & Jill Project – Beginning Guitar Lessons
- Paint & Sip
- Advanced Oil Painting
- Craft Academy

## Benefits
1. ✅ **Reliable**: API provides consistent, structured data
2. ✅ **Accurate**: Only classes are returned (no concerts or other events)
3. ✅ **Fast**: Direct API access without HTML parsing
4. ✅ **Complete**: Pagination ensures all classes are fetched
5. ✅ **Clean**: Proper HTML entity decoding for display

## Alternative Approach (Not Used)
We initially tried HTML filtering with CSS selectors but this didn't work because:
- The page loads events dynamically via JavaScript
- HTML scraping couldn't reliably capture all events
- BeautifulSoup couldn't access JS-rendered content

## Configuration
No changes needed to `sources.json` - the existing configuration works:
```json
{
  "name": "Turner Center for the Arts",
  "url": "https://turnercenter.org/events/",
  "type": "classes",
  "scraping_method": "ai_twostage"
}
```

The scraper automatically detects Turner Center + classes and uses the API.
