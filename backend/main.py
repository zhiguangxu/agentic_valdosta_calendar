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
# Serve React build in HF mode
# -----------------------------
if MODE == "HF":
    app.mount("/static", StaticFiles(directory="backend/static/static"), name="static")

    @app.get("/{full_path:path}")
    def serve_react_app(full_path: str):
        return FileResponse("backend/static/index.html")

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
    type: str  # "events" or "attractions"
    enabled: Optional[bool] = True
    scraping_method: Optional[str] = "auto"
    custom_selectors: Optional[dict] = None

class SourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    enabled: Optional[bool] = None
    scraping_method: Optional[str] = None
    custom_selectors: Optional[dict] = None

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
    Scrape a single source using the appropriate method
    """
    url = source['url']
    source_type = source['type']
    scraping_method = source.get('scraping_method', 'auto')
    custom_selectors = source.get('custom_selectors')
    site_scraper_name = source.get('site_scraper')  # NEW: Check for site-specific scraper

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # Method 1: Custom selectors (if provided and not using auto)
        if custom_selectors and scraping_method == 'calendar_table':
            print(f"  Using custom selectors (calendar table) for {url}")
            return generic_scraper.scrape_with_custom_selectors(url, custom_selectors, source_type, headers)

        # Method 2: AI-powered scraping (only if explicitly set to 'ai')
        elif scraping_method == 'ai' and client is not None:
            print(f"  Using AI scraping for {url}")
            return generic_scraper.scrape_with_ai(url, source_type, client)

        # Method 3: Generic auto-detection (default for 'auto' method)
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

        # Sort events by start date
        all_events.sort(key=lambda x: x["start"])

        return {
            "events": all_events,
            "attractions": attractions
        }

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# Helper functions for attraction deduplication and categorization
# -----------------------------
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
async def generate_events_stream():
    """
    Server-Sent Events endpoint that streams scraping progress and results.
    Allows frontend to update UI progressively as each source is scraped.
    """
    async def event_generator():
        try:
            # Load sources
            event_sources = source_manager.get_sources_by_type('events')
            attraction_sources = source_manager.get_sources_by_type('attractions')

            total_sources = len(event_sources) + len(attraction_sources)
            current = 0

            # Send initial progress
            yield f"data: {json.dumps({'type': 'init', 'total': total_sources, 'current': 0})}\n\n"

            # Get the event loop
            loop = asyncio.get_event_loop()

            # Scrape event sources
            for source in event_sources:
                try:
                    print(f"Scraping event source: {source['name']} ({source['url']})")

                    # Run blocking scrape_source in thread pool to avoid blocking the event loop
                    events = await loop.run_in_executor(executor, scrape_source, source)
                    current += 1

                    # Send events and progress update
                    yield f"data: {json.dumps({'type': 'events', 'events': events, 'source': source['name'], 'current': current, 'total': total_sources})}\n\n"
                    print(f"  Found {len(events)} events")
                except Exception as e:
                    print(f"Error scraping {source['name']}: {e}")
                    current += 1
                    # Send error update
                    yield f"data: {json.dumps({'type': 'error', 'source': source['name'], 'error': str(e), 'current': current, 'total': total_sources})}\n\n"

            # Scrape attraction sources and collect them for deduplication
            all_attractions = []
            for source in attraction_sources:
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
