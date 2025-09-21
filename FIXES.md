# Event Scraping and Calendar Fixes

## Issues Fixed

### 1. Missing Dependencies
- Added `beautifulsoup4` and `python-dateutil` to `requirements.txt`
- These were required for HTML parsing and date parsing functionality

### 2. Web Scraping Logic
- **Fixed visitvaldosta.org scraping**: Now properly targets `<article class="event">` elements
- **Improved date extraction**: Specifically looks for date and month information in the correct DOM structure
- **Enhanced valdostamainstreet.com scraping**: Added fallback logic with multiple date pattern matching
- **Better error handling**: Added try-catch blocks and debugging output

### 3. Date Parsing and Validation
- **Improved date parsing**: Uses `python-dateutil` for robust date parsing
- **Multiple date formats**: Supports various date formats (MM/DD/YYYY, Month DD YYYY, etc.)
- **Current year fallback**: Uses current year when year is not specified
- **Date validation**: Skips events without valid dates

### 4. FullCalendar Event Format
- **Fixed event structure**: Events now use proper FullCalendar format with `start` field
- **Removed deprecated fields**: Removed `date` and `time` fields in favor of `start`
- **Added `allDay` property**: Set to `false` for proper time display
- **Updated frontend**: Fixed event click and tooltip handling to use `extendedProps`

### 5. Frontend Integration
- **Fixed event properties**: Updated to use `extendedProps.url` and `extendedProps.description`
- **Improved tooltips**: Better handling of event descriptions and URLs
- **Event clicking**: Proper URL opening for event links

## Key Changes Made

### Backend (`main.py`)
1. Enhanced `scrape_site()` function with website-specific logic
2. Improved date parsing with multiple format support
3. Fixed event object structure for FullCalendar compatibility
4. Added debugging output for troubleshooting

### Frontend (`App.js`)
1. Updated event property access to use `extendedProps`
2. Fixed tooltip and click handling

### Dependencies (`requirements.txt`)
1. Added `beautifulsoup4` for HTML parsing
2. Added `python-dateutil` for robust date parsing

## Testing

Run the test script to verify functionality:
```bash
cd exp
python test_scraping.py
```

## Expected Results

- Events should now be properly extracted from both websites
- Events should appear on the correct dates in the calendar
- Event tooltips should show descriptions and links
- Clicking events should open the source URLs

## Debugging

The backend now includes debug output that will show:
- Number of event articles found
- Date parsing attempts and results
- Any parsing errors

Check the console output when running the backend to troubleshoot any remaining issues.
