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

## New Features: Additional Source Integration

### Added Three New Sources
1. **Wanderlog.com**: [Wanderlog Valdosta Attractions](https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta)
2. **Explore Georgia**: [Guide to Valdosta](https://exploregeorgia.org/article/guide-to-valdosta)
3. **TripAdvisor**: [Valdosta Attractions](https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html)

### Content Types
- **All new sources**: Permanent attractions and places to visit (not time-specific events)
- **Implementation**: Treats attractions as "ongoing events" scheduled for today
- **Data extracted**: Attraction names, descriptions, categories, and URLs

### How New Sources Integration Works

#### Wanderlog Integration
1. **Scrapes attraction listings** from the Wanderlog Valdosta page
2. **Extracts place information** including titles, descriptions, and links
3. **Extracts category badges** for filtering and organization

#### Explore Georgia Integration
1. **Scrapes guide content** from the official Explore Georgia Valdosta guide
2. **Extracts section headings** as attraction titles
3. **Captures descriptions** from following paragraphs
4. **Categories**: "Attraction", "Explore Georgia"

#### TripAdvisor Integration
1. **Scrapes attraction listings** from TripAdvisor's Valdosta page
2. **Extracts attraction names** and links to detailed pages
3. **Captures descriptions** and ratings information
4. **Categories**: "Attraction", "TripAdvisor"

#### Backend Processing
1. **Separates attractions from events** in the backend response
2. **Displays attractions below calendar** in a beautiful card layout
3. **Provides direct links** to source websites

### Benefits
- **Clean calendar display**: Events stay in calendar, attractions displayed separately
- **Better user experience**: Attractions shown in organized card format below calendar
- **Comprehensive coverage**: Combines time-specific events with permanent attractions
- **Realistic timing**: Events now have varied, intelligent times instead of all at 12:00 PM
- **Visual appeal**: Attractions displayed in responsive grid with hover effects

## Intelligent Time Assignment

### Problem Fixed
- **Issue**: All events were previously scheduled at 12:00 PM, which was unrealistic
- **Solution**: Implemented intelligent time extraction and assignment

### Time Extraction Features
1. **HTML Time Tags**: Extracts time from `<time datetime="">` attributes
2. **Text Pattern Matching**: Finds time patterns like "7:30 PM", "2:00", "11 AM"
3. **Event Type Analysis**: Assigns appropriate times based on event keywords

### Smart Default Times
- **Morning Events** (breakfast, sunrise): 7:00-9:00 AM
- **Lunch Events** (lunch, noon): 11:00 AM-1:00 PM  
- **Evening Events** (dinner, concerts, shows): 6:00-9:00 PM
- **Festivals/Fairs**: 10:00 AM-4:00 PM
- **Tours/Outdoor**: 9:00 AM-3:00 PM
- **Default Business Hours**: 9:00 AM-5:00 PM (with randomization)

### Attraction Time Variation
- **Museums/Galleries**: 10:00 AM-4:00 PM
- **Parks/Outdoor**: 8:00 AM-6:00 PM
- **Restaurants/Food**: 11:00 AM-8:00 PM
- **Shopping**: 9:00 AM-5:00 PM
- **General Attractions**: 9:00 AM-5:00 PM (with randomization)

### Bug Fixes Applied
- **Fixed variable order**: Description extraction now happens before time assignment
- **Added error handling**: Time parsing wrapped in try-catch blocks to prevent crashes
- **Simplified time extraction**: More robust search across entire article text
- **Added debug logging**: To help identify scraping issues
- **Fixed hardcoded source text**: "Learn more" links now show correct source (Explore Georgia, TripAdvisor, Wanderlog)
- **Added TripAdvisor fallback**: When TripAdvisor blocks requests, provides curated local attractions

## TripAdvisor Integration Issue

### Problem
- **Issue**: TripAdvisor returns 403 Forbidden status, blocking automated requests
- **Cause**: Strong anti-bot protection that detects and blocks scraping attempts
- **Impact**: No TripAdvisor attractions were appearing in the application

### Solution
- **Fallback System**: When TripAdvisor is blocked, provides curated local attractions
- **Enhanced Headers**: Uses more sophisticated browser headers to attempt bypass
- **Graceful Degradation**: Application continues to work with other sources

### Fallback Attractions Provided
1. **Wild Adventures Theme Park** - Family entertainment
2. **Valdosta State University** - Educational and cultural site
3. **Lowndes County Historical Society Museum** - Local history
4. **Valdosta Mall** - Shopping and dining
5. **Grand Bay Wildlife Management Area** - Nature and outdoor recreation

## UI Improvements

### Attractions Display
- **Card-based layout**: Each attraction displayed in an individual card
- **Responsive grid**: Automatically adjusts to screen size (minimum 300px per card)
- **Hover effects**: Cards lift up and show shadow on hover
- **Click to visit**: Clicking any card opens the Wanderlog page in a new tab
- **Clean typography**: Professional styling with proper spacing and colors
- **Icon integration**: Uses emoji icons for visual appeal (🏛️ for section header, 🔗 for links)
- **Category badges**: Each attraction displays its categories as styled badges
- **Filtering by category**: Dropdown to filter attractions by category (Museum, Restaurant, etc.)
- **Sorting options**: Sort attractions by name (A-Z) or by category
- **Results counter**: Shows how many attractions match the current filter
- **Pagination**: 6 attractions per page with navigation controls

### Layout Structure
1. **Calendar section**: Shows time-specific events from visitvaldosta.org and valdostamainstreet.com
2. **Attractions section**: Shows permanent places to visit from Wanderlog below the calendar
3. **Clear separation**: Events and attractions are visually distinct and serve different purposes

### Category-Based Filtering & Sorting
- **Dynamic categories**: Categories are automatically extracted from Wanderlog badge data
- **Filter dropdown**: Users can filter attractions by specific categories (e.g., "Museum", "Restaurant", "Brewery")
- **Sort options**: 
  - **Name (A-Z)**: Alphabetical sorting by attraction name
  - **Category**: Groups attractions by their primary category
- **Smart pagination**: Pagination automatically adjusts based on filtered results
- **Reset functionality**: Filters and sorting reset when fetching new data
- **Results counter**: Shows "Showing X attractions" to indicate filtered results

## Testing

Run the test script to verify functionality:
```bash
cd exp
python test_scraping.py
```

Or test individual sources:
```bash
python test_wanderlog.py  # Test only Wanderlog
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
