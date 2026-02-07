# backend/main.py
import os
import requests
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin
from typing import Optional, List, Dict

# Import new modules for flexible source management
try:
    # Try relative imports first (when run as module: uvicorn backend.main:app)
    from . import source_manager
    from . import generic_scraper
except ImportError:
    # Fall back to direct imports (when run from backend directory)
    import source_manager
    import generic_scraper

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# -----------------------------
# Setup
# -----------------------------
app = FastAPI()

# Get OpenAI API key with fallback
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please set your OpenAI API key as an environment variable or in a .env file.")
    print("You can set it by running: export OPENAI_API_KEY='your-api-key-here'")
    # Create a dummy client for now - the app will work but GPT features won't
    client = None
else:
    client = OpenAI(api_key=openai_api_key)

MODE = os.environ.get("ENV", "LOCAL")  # LOCAL or HF deploy

# -----------------------------
# CORS
# -----------------------------
if MODE == "LOCAL":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

# -----------------------------
# Mount static files in HF mode (but don't add catch-all route yet)
# -----------------------------
if MODE == "HF":
    app.mount("/static", StaticFiles(directory="backend/static/static"), name="static")

# -----------------------------
# Request models
# -----------------------------
class QueryRequest(BaseModel):
    query: str

class PasscodeRequest(BaseModel):
    passcode: str

class SourceRequest(BaseModel):
    name: str
    url: str
    type: str  # "events", "classes", "meetings", or "attractions"
    enabled: Optional[bool] = True
    scraping_method: Optional[str] = "auto"  # "auto", "ai", or "ai_twostage"

class SourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    enabled: Optional[bool] = None
    scraping_method: Optional[str] = None  # "auto", "ai", or "ai_twostage"

# -----------------------------
# OLD: Approved websites (now managed via sources.json)
# -----------------------------
# NOTE: This is no longer used - sources are now managed dynamically via the settings page
# and stored in sources.json. See source_manager.py for source management.
# APPROVED_SITES = [
#     "https://visitvaldosta.org/events/",
#     "https://www.valdostamainstreet.com/events-calendar",
#     "https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta",
#     "https://exploregeorgia.org/article/guide-to-valdosta",
#     "https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html",
# ]

# -----------------------------
# NOTE: TripAdvisor support has been removed
# TripAdvisor blocks scraping and is not supported
# -----------------------------

def scrape_source(source: Dict) -> List[Dict]:
    """
    Scrape a single source using the appropriate method.
    Supports 'auto' (generic pattern matching), 'ai' (AI-powered), and 'ai_twostage' (two-stage AI scraping).
    """
    url = source['url']
    source_type = source['type']
    scraping_method = source.get('scraping_method', 'auto')

    try:
        # Method 1: AI-powered scraping (including two-stage)
        if scraping_method in ['ai', 'ai_twostage'] and client is not None:
            print(f"  Using {scraping_method} scraping for {url}")
            return generic_scraper.scrape_with_ai(url, source_type, client, scraping_method)

        # Method 2: Generic auto-detection (default for 'auto' method or fallback)
        else:
            print(f"  Using generic auto-detection for {url}")
            return generic_scraper.scrape_generic_auto(url, source_type)

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []


# -----------------------------
# Generate events endpoint
# -----------------------------
@app.post("/generate_events")
def generate_events(request: QueryRequest):
    try:
        user_query = request.query.strip()
        all_events = []
        attractions = []

        # Step 1: Load and scrape enabled sources from configuration
        event_sources = source_manager.get_sources_by_type('events')
        attraction_sources = source_manager.get_sources_by_type('attractions')

        print(f"Scraping {len(event_sources)} event sources and {len(attraction_sources)} attraction sources")

        # Scrape event sources
        for source in event_sources:
            try:
                print(f"Scraping event source: {source['name']} ({source['url']})")
                events = scrape_source(source)
                all_events.extend(events)
                print(f"  Found {len(events)} events")
            except Exception as e:
                print(f"Error scraping {source['name']}: {e}")

        # Scrape attraction sources
        for source in attraction_sources:
            try:
                print(f"Scraping attraction source: {source['name']} ({source['url']})")
                source_attractions = scrape_source(source)
                attractions.extend(source_attractions)
                print(f"  Found {len(source_attractions)} attractions")
            except Exception as e:
                print(f"Error scraping {source['name']}: {e}")

        # Step 2: fallback to GPT if scraping yields too few events
        if len(all_events) < 5 and client is not None:
            # Determine month/year from query (simple regex)
            month_year_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', user_query, re.I)
            if month_year_match:
                month_name, year = month_year_match.groups()
                month_number = datetime.strptime(month_name, "%B").month
                year = int(year)
            else:
                now = datetime.today()
                month_number = now.month
                year = now.year

            system_prompt = f"""
            You are an assistant that generates events from a user query.
            User query: "{user_query}"
            Output: JSON array of events, each with:
            - title (string)
            - date (YYYY-MM-DD) within {month_number}/{year}
            - time (HH:MM)
            - url (string)
            - description (short text)
            Always return valid JSON only, no extra text.
            """
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": system_prompt}]
                )
                raw_output = response.choices[0].message.content.strip()
                if raw_output.startswith("```json"):
                    raw_output = raw_output[len("```json"):].strip()
                if raw_output.endswith("```"):
                    raw_output = raw_output[:-3].strip()
                try:
                    gpt_events = json.loads(raw_output)
                    # Assign deterministic dates within month/year
                    for idx, ev in enumerate(gpt_events):
                        ev_date = datetime(year, month_number, min(idx+1,28))  # avoid overflow
                        ev["start"] = f"{ev_date.strftime('%Y-%m-%d')}T{ev.get('time', '12:00')}:00"
                        ev["description"] = ev.get("description", "")
                        ev["url"] = ev.get("url", "")
                        ev["allDay"] = False
                        # Remove old date/time fields
                        ev.pop("date", None)
                        ev.pop("time", None)
                    all_events.extend(gpt_events)
                except Exception as e:
                    print(f"Failed to parse GPT events: {e}")
            except Exception as e:
                print(f"Failed to generate GPT events: {e}")
        elif len(all_events) < 5 and client is None:
            print("OpenAI client not available - skipping GPT fallback")

        # Deduplicate events across sources (same event from multiple sources)
        before_dedup = len(all_events)
        all_events = deduplicate_events(all_events)
        if before_dedup > len(all_events):
            print(f"Cross-source deduplication: {before_dedup} → {len(all_events)} events ({before_dedup - len(all_events)} duplicates removed)")

        # Sort events by start date
        all_events.sort(key=lambda x: x["start"])

        return {
            "events": all_events,
            "attractions": attractions
        }

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# Helper functions for event and attraction deduplication
# -----------------------------
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
            else:
                # Both have descriptions or both don't - prefer longer/more specific title
                if len(event.get('title', '')) > len(existing.get('title', '')):
                    print(f"    → Keeping current (longer title)")
                    best_events[dedup_key] = event
                else:
                    print(f"    → Keeping existing (longer or same title)")

    return list(best_events.values())


def deduplicate_classes(classes: List[Dict]) -> List[Dict]:
    """
    Remove duplicate classes across multiple sources.
    Classes are considered duplicates if they have the same date, instructor, and title.
    This is more permissive than events - allows same-named classes on different dates.
    """
    if not classes:
        return []

    # Use dict to store best class for each dedup_key
    best_classes = {}

    for cls in classes:
        # Create key from date + instructor + normalized title
        class_date = cls.get('start', '').split('T')[0]  # Get date part (YYYY-MM-DD)
        class_title = cls.get('title', '').lower().strip()

        # Try to extract instructor from title or description
        # Common patterns: "Class Name with Instructor Name", "Instructor: Name"
        instructor = ""
        description = cls.get('description', '').lower()

        # Look for "with [instructor]" or "by [instructor]" patterns
        import re
        instructor_match = re.search(r'(?:with|by|instructor:?)\s+([a-z\s]+?)(?:\||$|\.)', class_title + " " + description, re.I)
        if instructor_match:
            instructor = instructor_match.group(1).strip()[:30]

        # Normalize title for comparison (less aggressive than events)
        normalized = class_title

        # Remove common prefixes but keep ordinals (2nd Week is meaningful for classes)
        for prefix in ['class:', 'class ', 'workshop:', 'workshop ']:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]

        # Remove special characters for comparison
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())  # Normalize whitespace

        # Create deduplication key: date + instructor + title
        dedup_key = f"{class_date}_{instructor}_{normalized[:50]}"

        # If we haven't seen this class before, or if this class is better, keep it
        if dedup_key not in best_classes:
            best_classes[dedup_key] = cls
            print(f"  [DEDUP-CLASSES] New class: {class_title[:60]} on {class_date}")
        else:
            # Compare: prefer class with description, then longer title
            existing = best_classes[dedup_key]
            existing_desc = existing.get('description', '').strip()
            current_desc = cls.get('description', '').strip()

            print(f"  [DEDUP-CLASSES] Duplicate found:")
            print(f"    Existing: {existing.get('title', '')[:60]}")
            print(f"    Current:  {class_title[:60]}")
            print(f"    Key: {dedup_key}")

            # Prefer class with non-empty description
            if current_desc and not existing_desc:
                print(f"    → Keeping current (has description)")
                best_classes[dedup_key] = cls
            elif not current_desc and existing_desc:
                print(f"    → Keeping existing (has description)")
                pass  # Keep existing
            else:
                # Both have descriptions or both don't - prefer longer/more specific title
                if len(cls.get('title', '')) > len(existing.get('title', '')):
                    print(f"    → Keeping current (longer title)")
                    best_classes[dedup_key] = cls
                else:
                    print(f"    → Keeping existing (longer or same title)")

    return list(best_classes.values())


def deduplicate_meetings(meetings: List[Dict]) -> List[Dict]:
    """
    Remove duplicate meetings across multiple sources.
    Meetings are considered duplicates if they have the same date, location, and exact title.
    This is more strict than events - meetings need exact title match.
    """
    if not meetings:
        return []

    # Use dict to store best meeting for each dedup_key
    best_meetings = {}

    for meeting in meetings:
        # Create key from date + location + exact title
        meeting_date = meeting.get('start', '').split('T')[0]  # Get date part (YYYY-MM-DD)
        meeting_title = meeting.get('title', '').lower().strip()

        # Try to extract location from title or description
        location = ""
        description = meeting.get('description', '').lower()

        # Look for location patterns: "at [location]", "location: [place]"
        import re
        location_match = re.search(r'(?:at|location:?)\s+([a-z\s]+?)(?:\||$|\.)', meeting_title + " " + description, re.I)
        if location_match:
            location = location_match.group(1).strip()[:30]

        # For meetings, use exact title (only normalize whitespace)
        normalized = ' '.join(meeting_title.split())

        # Create deduplication key: date + location + exact title
        dedup_key = f"{meeting_date}_{location}_{normalized}"

        # If we haven't seen this meeting before, or if this meeting is better, keep it
        if dedup_key not in best_meetings:
            best_meetings[dedup_key] = meeting
            print(f"  [DEDUP-MEETINGS] New meeting: {meeting_title[:60]} on {meeting_date}")
        else:
            # Compare: prefer meeting with description, then longer title
            existing = best_meetings[dedup_key]
            existing_desc = existing.get('description', '').strip()
            current_desc = meeting.get('description', '').strip()

            print(f"  [DEDUP-MEETINGS] Duplicate found:")
            print(f"    Existing: {existing.get('title', '')[:60]}")
            print(f"    Current:  {meeting_title[:60]}")
            print(f"    Key: {dedup_key}")

            # Prefer meeting with non-empty description
            if current_desc and not existing_desc:
                print(f"    → Keeping current (has description)")
                best_meetings[dedup_key] = meeting
            elif not current_desc and existing_desc:
                print(f"    → Keeping existing (has description)")
                pass  # Keep existing
            else:
                # Both have descriptions or both don't - prefer longer/more specific title
                if len(meeting.get('title', '')) > len(existing.get('title', '')):
                    print(f"    → Keeping current (longer title)")
                    best_meetings[dedup_key] = meeting
                else:
                    print(f"    → Keeping existing (longer or same title)")

    return list(best_meetings.values())


def normalize_title(title: str) -> str:
    """Normalize title for deduplication (lowercase, remove special chars)"""
    import string
    title = title.lower().strip()
    # Remove common prefixes
    prefixes = ['visit:', 'visit ', 'explore:', 'explore ', 'the ', 'a ']
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    # Remove punctuation
    title = title.translate(str.maketrans('', '', string.punctuation))
    return title

def are_duplicates(title1: str, title2: str, threshold: float = 0.85) -> bool:
    """Check if two titles are duplicates using similarity ratio"""
    from difflib import SequenceMatcher
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold

def deduplicate_attractions(attractions: List[Dict]) -> List[Dict]:
    """Remove duplicate attractions based on title similarity"""
    if not attractions:
        return []

    unique_attractions = []
    for attraction in attractions:
        is_duplicate = False
        for existing in unique_attractions:
            if are_duplicates(attraction['title'], existing['title']):
                is_duplicate = True
                # Merge categories if both have them
                if 'categories' in attraction and 'categories' in existing:
                    existing_cats = set(existing.get('categories', []))
                    new_cats = set(attraction.get('categories', []))
                    existing['categories'] = list(existing_cats | new_cats)
                break

        if not is_duplicate:
            unique_attractions.append(attraction)

    print(f"Deduplication: {len(attractions)} → {len(unique_attractions)} attractions")
    return unique_attractions

def extract_categories(attraction: Dict) -> List[str]:
    """Automatically extract categories from attraction title and description"""
    categories = []
    text = (attraction.get('title', '') + ' ' + attraction.get('description', '')).lower()

    # Category keywords mapping
    category_keywords = {
        'Museum': ['museum', 'historical society', 'history', 'gallery', 'art center', 'arts'],
        'Park': ['park', 'garden', 'trail', 'outdoor', 'nature', 'wetland'],
        'Entertainment': ['theme park', 'entertainment', 'theater', 'theatre', 'show', 'concert', 'music', 'performance'],
        'Food & Drink': ['brewery', 'restaurant', 'cafe', 'coffee', 'food', 'dining', 'pecan', 'winery'],
        'Sports & Recreation': ['golf', 'sports', 'baseball', 'disc golf', 'wake', 'watersports', 'recreation'],
        'Shopping': ['market', 'shop', 'shopping', 'store', 'mall'],
        'Family Friendly': ['family', 'kids', 'children', 'playground', 'zoo', 'aquarium'],
        'Arts & Culture': ['art', 'cultural', 'gallery', 'theater', 'symphony', 'festival'],
        'Historic Site': ['historic', 'historical', 'heritage', 'monument', 'crescent'],
        'Event Venue': ['center', 'venue', 'auditorium', 'facility', 'hall']
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                categories.append(category)
                break  # Only add category once

    # If no categories found, assign a default based on title
    if not categories:
        if 'wild adventures' in text:
            categories = ['Entertainment', 'Family Friendly']
        else:
            categories = ['Attraction']

    return list(set(categories))  # Remove duplicates

# -----------------------------
# Generate events with progressive updates (SSE)
# -----------------------------
# Create a thread pool executor for running blocking scraping operations
executor = ThreadPoolExecutor(max_workers=1)

@app.get("/generate_events_stream")
async def generate_events_stream(category: str = "events"):
    """
    Server-Sent Events endpoint that streams scraping progress and results.
    Allows frontend to update UI progressively as each source is scraped.

    Args:
        category: The category to scrape (events, classes, meetings, or attractions)
    """
    async def event_generator():
        try:
            print(f"\n{'#'*80}")
            print(f"# STARTING STREAM FOR CATEGORY: {category.upper()}")
            print(f"{'#'*80}\n")

            # Load sources for the requested category
            sources = source_manager.get_sources_by_type(category)

            total_sources = len(sources)
            current = 0

            print(f"Loaded {total_sources} sources for category '{category}'")

            # Send initial progress
            yield f"data: {json.dumps({'type': 'init', 'total': total_sources, 'current': 0})}\n\n"

            # Get the event loop
            loop = asyncio.get_event_loop()

            # For calendar categories (events, classes, meetings), scrape each source with progress updates
            if category in ['events', 'classes', 'meetings']:
                print(f"\n{'='*80}")
                print(f"SCRAPING CATEGORY: {category.upper()}")
                print(f"{'='*80}")

                all_items = []
                for idx, source in enumerate(sources, 1):
                    try:
                        print(f"[{category.upper()}] ({idx}/{total_sources}) Scraping: {source['name']}")
                        print(f"[{category.upper()}]   URL: {source['url']}")
                        print(f"[{category.upper()}]   Type: {source['type']}")

                        # Validate source type matches category
                        if source['type'] != category:
                            print(f"[{category.upper()}] ⚠️  WARNING: Source type mismatch! Expected '{category}', got '{source['type']}'. Skipping.")
                            current += 1
                            error_msg = f"Type mismatch: expected {category}, got {source['type']}"
                            yield f"data: {json.dumps({'type': 'error', 'source': source['name'], 'error': error_msg, 'current': current, 'total': total_sources})}\n\n"
                            continue

                        # Run blocking scrape_source in thread pool
                        items = await loop.run_in_executor(executor, scrape_source, source)
                        current += 1

                        all_items.extend(items)

                        # Send progress update
                        progress_data = {
                            'type': 'progress',
                            'message': f'Scraped {len(items)} {category} from {source["name"]}',
                            'source': source['name'],
                            'current': current,
                            'total': total_sources
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        print(f"[{category.upper()}]   ✅ Found {len(items)} items")

                    except Exception as e:
                        print(f"[{category.upper()}]   ❌ Error: {e}")
                        current += 1
                        yield f"data: {json.dumps({'type': 'error', 'source': source['name'], 'error': str(e), 'current': current, 'total': total_sources})}\n\n"

                # Deduplicate and send all items using category-specific deduplication
                if all_items:
                    print(f"\n[{category.upper()}] Total items before deduplication: {len(all_items)}")

                    # Use category-specific deduplication function
                    if category == 'events':
                        unique_items = deduplicate_events(all_items)
                    elif category == 'classes':
                        unique_items = deduplicate_classes(all_items)
                    elif category == 'meetings':
                        unique_items = deduplicate_meetings(all_items)
                    else:
                        # Fallback to events deduplication for unknown categories
                        unique_items = deduplicate_events(all_items)

                    print(f"[{category.upper()}] Total items after deduplication: {len(unique_items)}")

                    # Sort by start date
                    unique_items.sort(key=lambda x: x["start"])

                    # Send deduplicated items with the correct type for the category
                    print(f"[{category.upper()}] Sending {len(unique_items)} items to frontend")
                    yield f"data: {json.dumps({'type': category, 'events': unique_items, 'source': 'All Sources (Deduplicated)', 'current': current, 'total': total_sources})}\n\n"
                else:
                    print(f"\n[{category.upper()}] No items to send")
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'No {category} found', 'source': 'Complete', 'current': current, 'total': total_sources})}\n\n"

            elif category == 'attractions':
                # Scrape attraction sources and collect them for deduplication
                all_attractions = []
                for source in sources:
                    try:
                        print(f"Scraping attraction source: {source['name']} ({source['url']})")

                        # Run blocking scrape_source in thread pool to avoid blocking the event loop
                        attractions = await loop.run_in_executor(executor, scrape_source, source)
                        current += 1

                        # Extract categories for each attraction
                        for attraction in attractions:
                            if 'categories' not in attraction or not attraction['categories']:
                                attraction['categories'] = extract_categories(attraction)

                        all_attractions.extend(attractions)

                        # Send progress update (but not attractions yet - we'll deduplicate first)
                        progress_data = {
                            'type': 'progress',
                            'message': f'Scraped {len(attractions)} attractions from {source["name"]}',
                            'source': source['name'],
                            'current': current,
                            'total': total_sources
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        print(f"  Found {len(attractions)} attractions")
                    except Exception as e:
                        print(f"Error scraping {source['name']}: {e}")
                        current += 1
                        # Send error update
                        yield f"data: {json.dumps({'type': 'error', 'source': source['name'], 'error': str(e), 'current': current, 'total': total_sources})}\n\n"

                # Deduplicate and send all attractions at once
                if all_attractions:
                    print(f"Total attractions before deduplication: {len(all_attractions)}")
                    unique_attractions = deduplicate_attractions(all_attractions)
                    print(f"Total attractions after deduplication: {len(unique_attractions)}")

                    # Send deduplicated attractions
                    yield f"data: {json.dumps({'type': 'attractions', 'attractions': unique_attractions, 'source': 'All Sources (Deduplicated)', 'current': current, 'total': total_sources})}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            print(f"Error in event_generator: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# -----------------------------
# Source Management API Endpoints
# -----------------------------

@app.post("/api/verify-passcode")
def verify_passcode_endpoint(request: PasscodeRequest):
    """Verify passcode for settings access"""
    try:
        is_valid = source_manager.verify_passcode(request.passcode)
        return {"valid": is_valid}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/sources")
def get_sources_endpoint(passcode: str):
    """Get all sources (requires passcode)"""
    try:
        if not source_manager.verify_passcode(passcode):
            raise HTTPException(status_code=403, detail="Invalid passcode")

        sources = source_manager.get_all_sources()
        return {"sources": sources}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources")
def add_source_endpoint(request: SourceRequest, passcode: str):
    """Add a new source (requires passcode)"""
    try:
        if not source_manager.verify_passcode(passcode):
            raise HTTPException(status_code=403, detail="Invalid passcode")

        source_dict = request.dict()
        new_source = source_manager.add_source(source_dict)
        return {"source": new_source, "message": "Source added successfully"}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        # Validation error (e.g., blocked URL)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sources/{source_id}")
def update_source_endpoint(source_id: str, request: SourceUpdateRequest, passcode: str):
    """Update an existing source (requires passcode)"""
    try:
        if not source_manager.verify_passcode(passcode):
            raise HTTPException(status_code=403, detail="Invalid passcode")

        updates = {k: v for k, v in request.dict().items() if v is not None}
        updated_source = source_manager.update_source(source_id, updates)

        if not updated_source:
            raise HTTPException(status_code=404, detail="Source not found")

        return {"source": updated_source, "message": "Source updated successfully"}
    except HTTPException as he:
        raise he
    except ValueError as ve:
        # Validation error (e.g., blocked URL)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sources/{source_id}")
def delete_source_endpoint(source_id: str, passcode: str):
    """Delete a source (requires passcode)"""
    try:
        if not source_manager.verify_passcode(passcode):
            raise HTTPException(status_code=403, detail="Invalid passcode")

        success = source_manager.delete_source(source_id)

        if not success:
            raise HTTPException(status_code=404, detail="Source not found")

        return {"message": "Source deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/update-passcode")
def update_passcode_endpoint(old_passcode: str, new_passcode: str):
    """Update the passcode (requires current passcode)"""
    try:
        if not source_manager.verify_passcode(old_passcode):
            raise HTTPException(status_code=403, detail="Invalid current passcode")

        source_manager.update_passcode(new_passcode)
        return {"message": "Passcode updated successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Serve React app (catch-all route - MUST be last!)
# -----------------------------
if MODE == "HF":
    @app.get("/{full_path:path}")
    def serve_react_app(full_path: str):
        return FileResponse("backend/static/index.html")
