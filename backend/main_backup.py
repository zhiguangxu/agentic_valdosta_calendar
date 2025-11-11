# backend/main.py
import os
import requests
import json
import re
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin

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
# Request model
# -----------------------------
class QueryRequest(BaseModel):
    query: str

# -----------------------------
# Approved websites
# -----------------------------
APPROVED_SITES = [
    "https://visitvaldosta.org/events/",
    "https://www.valdostamainstreet.com/events-calendar",
    "https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta",
    "https://exploregeorgia.org/article/guide-to-valdosta",
    "https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html",
]

# -----------------------------
# Fallback attractions for when TripAdvisor is blocked
# -----------------------------
def get_fallback_tripadvisor_attractions():
    """Provide fallback attractions when TripAdvisor is blocked"""
    today = datetime.now().strftime("%Y-%m-%d")
    import random
    
    fallback_attractions = [
        {
            "title": "Visit: Wild Adventures Theme Park",
            "url": "https://www.wildadventures.com/",
            "description": "Family-friendly theme park with rides, water park, and animal encounters",
            "categories": ["Attraction", "TripAdvisor"],
            "start": f"{today}T{random.randint(9, 17):02d}:00",
            "allDay": False
        },
        {
            "title": "Visit: Valdosta State University",
            "url": "https://www.valdosta.edu/",
            "description": "Beautiful university campus with historic buildings and cultural events",
            "categories": ["Attraction", "TripAdvisor"],
            "start": f"{today}T{random.randint(9, 17):02d}:00",
            "allDay": False
        },
        {
            "title": "Visit: Lowndes County Historical Society Museum",
            "url": "https://www.lowndescountyhistoricalsociety.org/",
            "description": "Local history museum showcasing Valdosta and Lowndes County heritage",
            "categories": ["Attraction", "TripAdvisor"],
            "start": f"{today}T{random.randint(10, 16):02d}:00",
            "allDay": False
        },
        {
            "title": "Visit: Valdosta Mall",
            "url": "https://www.valdostamall.com/",
            "description": "Shopping center with retail stores, dining, and entertainment",
            "categories": ["Attraction", "TripAdvisor"],
            "start": f"{today}T{random.randint(9, 21):02d}:00",
            "allDay": False
        },
        {
            "title": "Visit: Grand Bay Wildlife Management Area",
            "url": "https://georgiawildlife.com/grand-bay-wma",
            "description": "Nature preserve with hiking trails, bird watching, and outdoor recreation",
            "categories": ["Attraction", "TripAdvisor"],
            "start": f"{today}T{random.randint(8, 18):02d}:00",
            "allDay": False
        }
    ]
    
    print(f"Providing {len(fallback_attractions)} fallback TripAdvisor attractions")
    return fallback_attractions

# -----------------------------
# Scraping function with real date extraction
# -----------------------------
def scrape_site(url):
    # Use different headers for TripAdvisor to try to bypass blocking
    if "tripadvisor.com" in url:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        # For TripAdvisor, provide some fallback attractions if blocked
        if "tripadvisor.com" in url:
            print("TripAdvisor is blocked - providing fallback attractions")
            return get_fallback_tripadvisor_attractions()
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    events = []

    # Handle visitvaldosta.org structure
    if "visitvaldosta.org" in url:
        # Try multiple selectors to find events
        event_articles = soup.find_all("article", class_="event")
        if not event_articles:
            # Try alternative: look for event containers
            event_articles = soup.find_all("div", class_=re.compile(r".*event.*", re.I))
        if not event_articles:
            # Try finding sections with dates and event info
            event_articles = soup.find_all(["article", "div", "section"], class_=re.compile(r".*event|.*upcoming", re.I))
        
        print(f"Found {len(event_articles)} event articles on visitvaldosta.org")
        
        # If no articles found, try parsing from text patterns
        if not event_articles:
            # Look for date patterns followed by event titles
            # Pattern: "DD Month Event Title" or "Month DD Event Title"
            text_content = soup.get_text()
            # Look for patterns like "10 November", "13 November", etc.
            date_event_pattern = re.compile(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(.+?)(?=\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)|$)', re.DOTALL)
            matches = date_event_pattern.findall(text_content)
            
            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month
            
            # Month name to number mapping
            month_names = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            for match in matches:
                try:
                    day, month_name, event_text = match
                    day = int(day)
                    month_num = month_names.get(month_name, current_month)
                    
                    # Determine the year: if the month is before current month, assume next year
                    # (e.g., if we're in November and see January, it's next year)
                    # Also, if we're near the end of the year and see early months, it's next year
                    event_year = current_year
                    if month_num < current_month:
                        # Month is earlier in the year (e.g., January when we're in November)
                        event_year = current_year + 1
                    elif month_num == current_month:
                        # Same month - check if day has passed
                        if day < current_date.day:
                            # Day has passed, could be next year for recurring events
                            # But for a single events page, it's more likely current year
                            # We'll keep it as current year unless it's clearly in the past
                            test_date = dateparser.parse(f"{month_name} {day}, {current_year}")
                            if test_date and test_date < current_date - timedelta(days=7):
                                # If more than a week in the past, assume next year
                                event_year = current_year + 1
                    # If month_num > current_month, it's current year (future month in same year)
                    
                    # Parse the event text to extract title and description
                    lines = event_text.strip().split('\n')
                    title = lines[0].strip() if lines else ""
                    description = ' '.join(lines[1:]).strip() if len(lines) > 1 else ""
                    
                    # Clean up title (remove extra whitespace, "learn more", etc.)
                    title = re.sub(r'\s+', ' ', title).strip()
                    title = re.sub(r'\blearn more\b', '', title, flags=re.I).strip()
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Parse date with determined year
                    try:
                        date_str = f"{month_name} {day}, {event_year}"
                        dt = dateparser.parse(date_str)
                        if dt:
                            date_str = dt.strftime("%Y-%m-%d")
                        else:
                            continue
                    except Exception as e:
                        print(f"Date parsing error for {date_str}: {e}")
                        continue
                    
                    # Extract time from description
                    time_str = None
                    time_patterns = [
                        r'\b(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)\b',
                        r'\b(\d{1,2})\s*(?:AM|PM|am|pm)\b',
                        r'\b(\d{1,2}):(\d{2})\b',
                        r'at\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',
                        r'(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',
                    ]
                    
                    for pattern in time_patterns:
                        match_time = re.search(pattern, event_text, re.I)
                        if match_time:
                            try:
                                if len(match_time.groups()) == 2:  # HH:MM format
                                    hour, minute = match_time.groups()
                                    hour_int = int(hour)
                                    if 'PM' in match_time.group(0).upper() and hour_int != 12:
                                        hour_int += 12
                                    elif 'AM' in match_time.group(0).upper() and hour_int == 12:
                                        hour_int = 0
                                    time_str = f"{hour_int:02d}:{minute}"
                                else:  # H AM/PM format
                                    hour = match_time.group(1)
                                    hour_int = int(hour)
                                    if 'PM' in match_time.group(0).upper() and hour_int != 12:
                                        hour_int += 12
                                    elif 'AM' in match_time.group(0).upper() and hour_int == 12:
                                        hour_int = 0
                                    time_str = f"{hour_int:02d}:00"
                                break
                            except (ValueError, IndexError):
                                continue
                    
                    # Set intelligent default time if none found
                    if not time_str:
                        import random
                        event_text_lower = (title + " " + description).lower()
                        
                        if any(word in event_text_lower for word in ["breakfast", "morning", "dawn", "sunrise"]):
                            time_str = f"{random.randint(7, 9):02d}:00"
                        elif any(word in event_text_lower for word in ["lunch", "noon", "midday"]):
                            time_str = f"{random.randint(11, 13):02d}:00"
                        elif any(word in event_text_lower for word in ["dinner", "evening", "sunset", "night", "concert", "show", "performance"]):
                            time_str = f"{random.randint(18, 21):02d}:00"
                        elif any(word in event_text_lower for word in ["festival", "fair", "market", "exhibition"]):
                            time_str = f"{random.randint(10, 16):02d}:00"
                        elif any(word in event_text_lower for word in ["tour", "walking", "hiking", "outdoor"]):
                            time_str = f"{random.randint(9, 15):02d}:00"
                        else:
                            time_str = f"{random.randint(9, 17):02d}:00"
                    
                    print(f"Adding event: {title} at {date_str}T{time_str}:00")
                    events.append({
                        "title": title,
                        "url": url,
                        "description": description,
                        "start": f"{date_str}T{time_str}:00",
                        "allDay": False
                    })
                except Exception as e:
                    print(f"Error parsing text-based event: {e}")
                    continue
        
        # Also try the original article-based parsing
        for article in event_articles:
            try:
                # Extract title from h3, h2, or strong/bold text
                title_elem = article.find(["h3", "h2", "h4", "strong", "b"])
                if not title_elem:
                    # Try getting text from first link
                    link_elem = article.find("a")
                    if link_elem:
                        title = link_elem.get_text(strip=True)
                    else:
                        continue
                else:
                    title = title_elem.get_text(strip=True)
                
                if not title or len(title) < 3:
                    continue
                
                # Extract date information - try multiple approaches
                date_str = None
                month_text = None
                day = None
                
                # Method 1: Look for div.date and div.txt structure
                date_elem = article.find("div", class_="date")
                month_elem = article.find("div", class_="txt")
                
                if date_elem and month_elem:
                    day_span = date_elem.find("span")
                    month_span = month_elem.find("span")
                    if day_span and month_span:
                        day = day_span.get_text(strip=True)
                        month_text = month_span.get_text(strip=True)
                
                # Method 2: Look for date patterns in text
                if not date_str:
                    article_text = article.get_text()
                    date_pattern = re.search(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)', article_text, re.I)
                    if date_pattern:
                        day = date_pattern.group(1)
                        month_text = date_pattern.group(2)
                
                if day and month_text:
                    current_date = datetime.now()
                    current_year = current_date.year
                    current_month = current_date.month
                    
                    # Month name to number mapping
                    month_names = {
                        'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                        'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
                    }
                    
                    month_num = month_names.get(month_text, current_month)
                    
                    # Determine the year: if the month is before current month, assume next year
                    event_year = current_year
                    if month_num < current_month:
                        # Month is earlier in the year (e.g., January when we're in November)
                        event_year = current_year + 1
                    elif month_num == current_month:
                        # Same month - check if day has passed
                        if int(day) < current_date.day:
                            # Day has passed, check if it's clearly in the past
                            test_date = dateparser.parse(f"{month_text} {day}, {current_year}")
                            if test_date and test_date < current_date - timedelta(days=7):
                                # If more than a week in the past, assume next year
                                event_year = current_year + 1
                    # If month_num > current_month, it's current year (future month in same year)
                    
                    try:
                        date_str_full = f"{month_text} {day}, {event_year}"
                        dt = dateparser.parse(date_str_full)
                        if dt:
                            date_str = dt.strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"Date parsing error: {e}")
                        continue
                
                if not date_str:
                    continue
                
                # Extract time information
                time_str = None
                article_text = article.get_text()
                time_patterns = [
                    r'\b(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)\b',
                    r'\b(\d{1,2})\s*(?:AM|PM|am|pm)\b',
                    r'at\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',
                    r'(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',
                ]
                
                for pattern in time_patterns:
                    match = re.search(pattern, article_text, re.I)
                    if match:
                        try:
                            if len(match.groups()) == 2:  # HH:MM format
                                hour, minute = match.groups()
                                hour_int = int(hour)
                                if 'PM' in match.group(0).upper() and hour_int != 12:
                                    hour_int += 12
                                elif 'AM' in match.group(0).upper() and hour_int == 12:
                                    hour_int = 0
                                time_str = f"{hour_int:02d}:{minute}"
                            else:  # H AM/PM format
                                hour = match.group(1)
                                hour_int = int(hour)
                                if 'PM' in match.group(0).upper() and hour_int != 12:
                                    hour_int += 12
                                elif 'AM' in match.group(0).upper() and hour_int == 12:
                                    hour_int = 0
                                time_str = f"{hour_int:02d}:00"
                            break
                        except (ValueError, IndexError):
                            continue
                
                # Extract description
                desc_elem = article.find("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Set intelligent default time if none found
                if not time_str:
                    import random
                    event_text = (title + " " + description).lower()
                    
                    if any(word in event_text for word in ["breakfast", "morning", "dawn", "sunrise"]):
                        time_str = f"{random.randint(7, 9):02d}:00"
                    elif any(word in event_text for word in ["lunch", "noon", "midday"]):
                        time_str = f"{random.randint(11, 13):02d}:00"
                    elif any(word in event_text for word in ["dinner", "evening", "sunset", "night", "concert", "show", "performance"]):
                        time_str = f"{random.randint(18, 21):02d}:00"
                    elif any(word in event_text for word in ["festival", "fair", "market", "exhibition"]):
                        time_str = f"{random.randint(10, 16):02d}:00"
                    elif any(word in event_text for word in ["tour", "walking", "hiking", "outdoor"]):
                        time_str = f"{random.randint(9, 15):02d}:00"
                    else:
                        time_str = f"{random.randint(9, 17):02d}:00"
                
                # Extract URL
                link_elem = article.find("a", href=True)
                event_url = url
                if link_elem and link_elem.get("href"):
                    event_url = link_elem["href"]
                    if event_url.startswith("/"):
                        event_url = urljoin(url, event_url)
                
                print(f"Adding event: {title} at {date_str}T{time_str}:00")
                events.append({
                    "title": title,
                    "url": event_url,
                    "description": description,
                    "start": f"{date_str}T{time_str}:00",
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing event article: {e}")
                continue
    
    # Handle wanderlog.com structure
    elif "wanderlog.com" in url:
        print(f"Scraping Wanderlog attractions for Valdosta")
        # Look for attraction/place entries
        place_views = soup.find_all("div", class_="PlaceView__selectable")
        for place_view in place_views:
            try:
                # Extract title from h2 link
                title_elem = place_view.find("h2")
                if not title_elem:
                    continue
                title_link = title_elem.find("a")
                if not title_link:
                    continue
                title = title_link.get_text(strip=True)
                
                # Extract categories from badges
                categories = []
                badge_elements = place_view.find_all("div", class_="badge")
                for badge in badge_elements:
                    category_text = badge.get_text(strip=True)
                    if category_text and len(category_text) > 0:
                        categories.append(category_text)
                
                # Extract description
                desc_elem = place_view.find("div", class_="mt-2")
                description = ""
                if desc_elem:
                    # Get the description text (skip badges)
                    desc_text = desc_elem.get_text(strip=True)
                    # Remove badge text and get the main description
                    lines = desc_text.split('\n')
                    for line in lines:
                        if len(line) > 50 and not any(badge in line.lower() for badge in ['mentioned on', 'lists', 'google', 'tripadvisor']):
                            description = line
                            break
                
                # Extract URL
                place_url = title_link.get("href", "")
                if place_url.startswith("/"):
                    place_url = f"https://wanderlog.com{place_url}"
                
                    # Create an "ongoing attraction" event for today with varied times
                    today = datetime.now().strftime("%Y-%m-%d")
                    import random
                    
                    # Vary attraction times based on type
                    attraction_text = (title + " " + description).lower()
                    if any(word in attraction_text for word in ["museum", "gallery", "exhibition", "art"]):
                        time_str = f"{random.randint(10, 16):02d}:00"
                    elif any(word in attraction_text for word in ["park", "garden", "outdoor", "nature", "hiking"]):
                        time_str = f"{random.randint(8, 18):02d}:00"
                    elif any(word in attraction_text for word in ["restaurant", "cafe", "food", "dining"]):
                        time_str = f"{random.randint(11, 20):02d}:00"
                    elif any(word in attraction_text for word in ["shop", "store", "market", "shopping"]):
                        time_str = f"{random.randint(9, 17):02d}:00"
                    else:
                        time_str = f"{random.randint(9, 17):02d}:00"

                    events.append({
                        "title": f"Visit: {title}",
                        "url": place_url,
                        "description": description,
                        "categories": categories,
                        "start": f"{today}T{time_str}:00",
                        "allDay": False
                    })
            except Exception as e:
                print(f"Error parsing Wanderlog place: {e}")
                continue
    
    # Handle valdostamainstreet.com structure (calendar table)
    elif "valdostamainstreet.com" in url:
        print(f"Scraping valdostamainstreet.com calendar")

        # FIXED: Scrape multiple months (current and next 2 months) to get all upcoming events
        # The calendar uses ?month=YYYY-MM parameter to show different months
        months_to_scrape = []

        # If URL doesn't specify a month, scrape current and next 2 months
        if "?month=" not in url:
            current_date = datetime.now()

            # Generate URLs for current month and next 2 months
            for month_offset in range(3):
                year = current_date.year
                month = current_date.month + month_offset

                # Handle year rollover
                while month > 12:
                    month -= 12
                    year += 1

                month_url = f"{url}?month={year}-{month:02d}"
                months_to_scrape.append(month_url)
                print(f"Will scrape: {month_url}")
        else:
            # If URL already specifies a month, just scrape that one
            months_to_scrape = [url]

        # Scrape each month
        for month_url in months_to_scrape:
            try:
                # Fetch the month's calendar
                if month_url != url:
                    resp_month = requests.get(month_url, headers=headers, timeout=15)
                    resp_month.raise_for_status()
                    soup = BeautifulSoup(resp_month.text, "html.parser")
                    print(f"Fetched calendar for {month_url}")

                # Find the calendar table
                calendar_table = soup.find("table")
                if not calendar_table:
                    # Try finding calendar container
                    calendar_div = soup.find("div", class_=re.compile(r".*calendar.*", re.I))
                    if calendar_div:
                        calendar_table = calendar_div.find("table")

                if not calendar_table:
                    print(f"No calendar table found for {month_url}")
                    continue

                # Process this month's calendar
                # Extract month and year from page
                month_year_elem = soup.find(["h1", "h2", "h3"], string=re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"))
                if not month_year_elem:
                    # Try finding in other elements
                    month_year_text = soup.get_text()
                    month_year_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', month_year_text, re.I)
                    if month_year_match:
                        month_name = month_year_match.group(1)
                        year = int(month_year_match.group(2))
                    else:
                        # Default to current month/year
                        now = datetime.now()
                        month_name = now.strftime("%B")
                        year = now.year
                else:
                    month_year_text = month_year_elem.get_text()
                    month_year_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', month_year_text, re.I)
                    if month_year_match:
                        month_name = month_year_match.group(1)
                        year = int(month_year_match.group(2))
                    else:
                        now = datetime.now()
                        month_name = now.strftime("%B")
                        year = now.year
            
                # Month name to number mapping
                month_names_to_num = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                month_num = month_names_to_num.get(month_name, datetime.now().month)
            
                # Find all table rows (skip header row)
                rows = calendar_table.find_all("tr")
                print(f"Found {len(rows)} rows in calendar table for {month_name} {year}")
            
                # Better approach: collect all days first, then determine month boundaries
                # Calendar typically shows: previous month days (high numbers) -> current month -> next month days (low numbers)
                all_calendar_days = []
                for row_idx, row in enumerate(rows):
                    if row_idx == 0:
                        continue
                    cells = row.find_all(["td", "th"])
                    row_days = []
                    for cell in cells:
                        day_text = cell.get_text(strip=True)
                        day_match = re.search(r'^(\d{1,2})', day_text)
                        if day_match:
                            row_days.append(int(day_match.group(1)))
                    if row_days:
                        all_calendar_days.append(row_days)
            
                # Simplified approach: determine month based on day number and position
                # Previous month: days > 20 in first row
                # Current month: days 1-31 in middle rows, or day 1 in first row after high numbers
                # Next month: days 1-7 in last row after day 30
                first_transition = None
                second_transition = None
            
                # Find first transition: look for day 1 in first row (current month start)
                if all_calendar_days:
                    first_row = all_calendar_days[0]
                    if 1 in first_row:
                        day_1_idx = first_row.index(1)
                        first_transition = (1, day_1_idx)
                        print(f"First transition found at row 1, cell {day_1_idx} (day 1)")
            
                # Find second transition: look for day 1 in last row after a high number (next month start)
                if all_calendar_days and len(all_calendar_days) > 1:
                    last_row = all_calendar_days[-1]
                    last_row_idx = len(all_calendar_days)  # This is the row_idx in the rows enumeration (1-based after header)
                    if 1 in last_row and max(last_row) > 20:
                        # Find where day 1 appears after a high number
                        for cell_idx, day in enumerate(last_row):
                            if day == 1 and cell_idx > 0 and last_row[cell_idx - 1] > 20:
                                second_transition = (last_row_idx, cell_idx)
                                print(f"Second transition found at row {last_row_idx}, cell {cell_idx} (day 1 after day {last_row[cell_idx - 1]})")
                                break
                        # If not found, day 1 at start of last row with high numbers is also next month
                        if not second_transition and last_row[0] == 1 and max(last_row) > 20:
                            second_transition = (last_row_idx, 0)
                            print(f"Second transition found at row {last_row_idx}, cell 0 (day 1 at start)")
            
                # Now process the calendar
                for row_idx, row in enumerate(rows):
                    # Skip header row
                    if row_idx == 0:
                        continue

                    # Find all cells in this row
                    cells = row.find_all(["td", "th"])

                    for cell_idx, cell in enumerate(cells):
                        # Find all event links in this cell
                        event_links = cell.find_all("a", href=True)

                        # Skip cells without events
                        if not event_links:
                            continue

                        # FIXED: Use data-date attribute instead of extracting from text
                        # The calendar has a special structure where event cells have data-date attributes
                        # that contain the correct ISO format date (e.g., "2025-11-02")
                        data_date = cell.get("data-date", "")

                        if data_date:
                            # Use the data-date attribute directly
                            try:
                                dt = dateparser.parse(data_date)
                                if dt:
                                    date_str = dt.strftime("%Y-%m-%d")
                                    day = dt.day
                                    event_month = dt.month
                                    event_year = dt.year
                                else:
                                    continue
                            except Exception as e:
                                print(f"Error parsing data-date {data_date}: {e}")
                                continue
                        else:
                            # Fallback: Extract day number from text (old logic)
                            day_text = cell.get_text(strip=True)
                            day_match = re.search(r'^(\d{1,2})', day_text)
                            if not day_match:
                                continue

                            day = int(day_match.group(1))

                            # Determine which month this day belongs to
                            event_month = month_num
                            event_year = year

                            # Simple heuristic:
                            # - Days > 20 in first row = previous month
                            # - Days 1-31 in middle = current month (default)
                            # - Days 1-7 in last row after day 30 = next month

                            # Check if this is from previous month (high numbers in first data row)
                            if row_idx == 1 and day > 20:
                                event_month = month_num - 1
                                if event_month == 0:
                                    event_month = 12
                                    event_year = year - 1
                            # Check if this is from next month (in the transition row or after)
                            elif second_transition:
                                if row_idx == second_transition[0]:
                                    # In the transition row, check if we're at or after the transition point
                                    if cell_idx >= second_transition[1]:
                                        event_month = month_num + 1
                                        if event_month == 13:
                                            event_month = 1
                                            event_year = year + 1
                                elif row_idx > second_transition[0]:
                                    # After the transition row, all days are next month
                                    event_month = month_num + 1
                                    if event_month == 13:
                                        event_month = 1
                                        event_year = year + 1
                            # Default: current month (most days fall here)

                            # Parse the date with correct month/year
                            try:
                                month_name_for_date = list(month_names_to_num.keys())[list(month_names_to_num.values()).index(event_month)]
                                date_str_full = f"{month_name_for_date} {day}, {event_year}"
                                dt = dateparser.parse(date_str_full)
                                if dt:
                                    date_str = dt.strftime("%Y-%m-%d")
                                else:
                                    continue
                            except Exception as e:
                                print(f"Date parsing error for {date_str_full}: {e}")
                                continue

                        # Process all event links found in this cell
                        for link in event_links:
                            try:
                                event_text = link.get_text(strip=True)
                                if not event_text or len(event_text) < 3:
                                    continue
                            
                                # Skip navigation links
                                if any(word in event_text.lower() for word in ["prev", "next", "«", "»"]):
                                    continue
                            
                                # Get the full link
                                event_url = link.get("href", "")
                                if event_url.startswith("/"):
                                    event_url = urljoin(url, event_url)
                            
                                # Extract time from link text or cell text
                                time_str = None
                                cell_text = cell.get_text()
                            
                                # Look for time patterns like "1:00 pm to 4:00 pm" or "5:00 pm"
                                time_patterns = [
                                    r'(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)\s+to\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',  # Range
                                    r'(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',  # Single time
                                    r'(\d{1,2})\s*(?:AM|PM|am|pm)',  # Hour only
                                ]
                            
                                for pattern in time_patterns:
                                    match = re.search(pattern, cell_text, re.I)
                                    if match:
                                        try:
                                            if len(match.groups()) == 4:  # Time range
                                                # Use start time
                                                hour, minute = match.groups()[0], match.groups()[1]
                                                hour_int = int(hour)
                                                if 'PM' in match.group(0).upper() and hour_int != 12:
                                                    hour_int += 12
                                                elif 'AM' in match.group(0).upper() and hour_int == 12:
                                                    hour_int = 0
                                                time_str = f"{hour_int:02d}:{minute}"
                                            elif len(match.groups()) == 2:  # HH:MM format
                                                hour, minute = match.groups()
                                                hour_int = int(hour)
                                                if 'PM' in match.group(0).upper() and hour_int != 12:
                                                    hour_int += 12
                                                elif 'AM' in match.group(0).upper() and hour_int == 12:
                                                    hour_int = 0
                                                time_str = f"{hour_int:02d}:{minute}"
                                            else:  # H AM/PM format
                                                hour = match.group(1)
                                                hour_int = int(hour)
                                                if 'PM' in match.group(0).upper() and hour_int != 12:
                                                    hour_int += 12
                                                elif 'AM' in match.group(0).upper() and hour_int == 12:
                                                    hour_int = 0
                                                time_str = f"{hour_int:02d}:00"
                                            break
                                        except (ValueError, IndexError):
                                            continue
                            
                                # Set default time if not found
                                if not time_str:
                                    import random
                                    event_text_lower = event_text.lower()

                                    if any(word in event_text_lower for word in ["breakfast", "morning"]):
                                        time_str = f"{random.randint(7, 9):02d}:00"
                                    elif any(word in event_text_lower for word in ["lunch", "noon", "midday"]):
                                        time_str = f"{random.randint(11, 13):02d}:00"
                                    elif any(word in event_text_lower for word in ["dinner", "evening", "night", "concert", "show"]):
                                        time_str = f"{random.randint(18, 21):02d}:00"
                                    elif any(word in event_text_lower for word in ["market", "fair", "festival"]):
                                        time_str = f"{random.randint(9, 16):02d}:00"
                                    else:
                                        time_str = f"{random.randint(9, 17):02d}:00"
                            
                                # Extract description from link title or nearby text
                                description = ""
                                link_title = link.get("title", "")
                                if link_title:
                                    description = link_title
                                else:
                                    # Try to get description from parent or sibling elements
                                    parent = link.find_parent()
                                    if parent:
                                        # Look for description in the same cell
                                        cell_text_clean = cell.get_text(separator=" ").strip()
                                        # Remove the event title and time to get description
                                        desc_text = re.sub(re.escape(event_text), "", cell_text_clean, flags=re.I)
                                        desc_text = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm).*', '', desc_text, flags=re.I)
                                        description = desc_text.strip()
                            
                                print(f"Adding event: {event_text} at {date_str}T{time_str}:00")
                                events.append({
                                    "title": event_text,
                                    "url": event_url,
                                    "description": description,
                                    "start": f"{date_str}T{time_str}:00",
                                    "allDay": False
                                })
                            except Exception as e:
                                print(f"Error parsing event link: {e}")
                                continue

            except Exception as e:
                print(f"Error scraping calendar for {month_url}: {e}")
                continue

    # Handle exploregeorgia.org structure
    elif "exploregeorgia.org" in url:
        print(f"Scraping Explore Georgia guide for Valdosta")
        # Look for attraction/place entries in the article
        attraction_sections = soup.find_all(["h2", "h3", "h4"])
        for section in attraction_sections:
            try:
                title = section.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                
                # Skip generic headings
                skip_words = ["introduction", "getting", "where", "when", "how", "about", "contact"]
                if any(word in title.lower() for word in skip_words):
                    continue
                
                # Extract description from next paragraph
                description = ""
                next_elem = section.find_next(["p", "div"])
                if next_elem:
                    description = next_elem.get_text(strip=True)[:200]
                
                # Create attraction entry with varied time
                today = datetime.now().strftime("%Y-%m-%d")
                import random
                
                # Vary attraction times based on type
                attraction_text = (title + " " + description).lower()
                if any(word in attraction_text for word in ["museum", "gallery", "exhibition", "art"]):
                    time_str = f"{random.randint(10, 16):02d}:00"
                elif any(word in attraction_text for word in ["park", "garden", "outdoor", "nature", "hiking"]):
                    time_str = f"{random.randint(8, 18):02d}:00"
                elif any(word in attraction_text for word in ["restaurant", "cafe", "food", "dining"]):
                    time_str = f"{random.randint(11, 20):02d}:00"
                elif any(word in attraction_text for word in ["shop", "store", "market", "shopping"]):
                    time_str = f"{random.randint(9, 17):02d}:00"
                else:
                    time_str = f"{random.randint(9, 17):02d}:00"
                
                events.append({
                    "title": f"Explore: {title}",
                    "url": url,
                    "description": description,
                    "categories": ["Attraction", "Explore Georgia"],
                    "start": f"{today}T{time_str}:00",
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing Explore Georgia section: {e}")
                continue

    # Handle tripadvisor.com structure
    elif "tripadvisor.com" in url:
        print(f"Scraping TripAdvisor attractions for Valdosta")
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        print(f"Page content length: {len(soup.get_text())}")
        
        # Check if we got blocked
        if "please enable javascript" in soup.get_text().lower() or "captcha" in soup.get_text().lower():
            print("TripAdvisor appears to be blocking requests - got captcha/JS page")
            return events
        # Look for attraction entries
        attraction_items = soup.find_all("div", class_=["attraction_element", "listing_title", "property_title"])
        print(f"Found {len(attraction_items)} items with primary selectors")
        
        if not attraction_items:
            # Try alternative selectors
            attraction_items = soup.find_all("a", href=re.compile(r"/Attraction_Review-"))
            print(f"Found {len(attraction_items)} items with alternative selectors")
        
        # Try even more generic selectors if still nothing
        if not attraction_items:
            attraction_items = soup.find_all("div", class_=re.compile(r".*attraction.*|.*listing.*|.*property.*"))
            print(f"Found {len(attraction_items)} items with generic selectors")
        
        # Try finding any div with attraction-related text
        if not attraction_items:
            attraction_items = soup.find_all("div", string=re.compile(r".*attraction.*|.*museum.*|.*park.*|.*restaurant.*", re.I))
            print(f"Found {len(attraction_items)} items with text-based selectors")
        
        for i, item in enumerate(attraction_items):
            try:
                print(f"Processing TripAdvisor item {i+1}/{len(attraction_items)}")
                # Extract title
                title_elem = item.find(["h3", "h4", "span", "a"])
                if not title_elem:
                    print(f"  No title element found")
                    continue
                title = title_elem.get_text(strip=True)
                print(f"  Title: {title}")
                
                if not title or len(title) < 3:
                    print(f"  Title too short or empty")
                    continue
                
                # Extract URL
                link_elem = item.find("a", href=True)
                place_url = ""
                if link_elem:
                    place_url = link_elem["href"]
                    if place_url.startswith("/"):
                        place_url = f"https://www.tripadvisor.com{place_url}"
                
                # Extract description
                description = ""
                desc_elem = item.find(["p", "div", "span"])
                if desc_elem:
                    description = desc_elem.get_text(strip=True)[:200]
                
                # Create attraction entry with varied time
                today = datetime.now().strftime("%Y-%m-%d")
                import random
                
                # Vary attraction times based on type
                attraction_text = (title + " " + description).lower()
                if any(word in attraction_text for word in ["museum", "gallery", "exhibition", "art"]):
                    time_str = f"{random.randint(10, 16):02d}:00"
                elif any(word in attraction_text for word in ["park", "garden", "outdoor", "nature", "hiking"]):
                    time_str = f"{random.randint(8, 18):02d}:00"
                elif any(word in attraction_text for word in ["restaurant", "cafe", "food", "dining"]):
                    time_str = f"{random.randint(11, 20):02d}:00"
                elif any(word in attraction_text for word in ["shop", "store", "market", "shopping"]):
                    time_str = f"{random.randint(9, 17):02d}:00"
                else:
                    time_str = f"{random.randint(9, 17):02d}:00"
                
                print(f"  Adding TripAdvisor attraction: {title}")
                events.append({
                    "title": f"Visit: {title}",
                    "url": place_url or url,
                    "description": description,
                    "categories": ["Attraction", "TripAdvisor"],
                    "start": f"{today}T{time_str}:00",
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing TripAdvisor attraction: {e}")
                continue

    # Handle any other sites (fallback)
    else:
        print(f"No specific handler for {url}, skipping...")

    # Filter out past events
    current_datetime = datetime.now()
    filtered_events = []
    for event in events:
        try:
            # Parse the event start date
            event_start_str = event.get("start", "")
            if event_start_str:
                # Handle ISO format: "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DDTHH:MM"
                if "T" in event_start_str:
                    event_date_str = event_start_str.split("T")[0]
                else:
                    event_date_str = event_start_str
                
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                # Only include events that are today or in the future
                if event_date.date() >= current_datetime.date():
                    filtered_events.append(event)
                else:
                    print(f"Filtering out past event: {event.get('title', 'Unknown')} on {event_date_str}")
        except Exception as e:
            print(f"Error filtering event {event.get('title', 'Unknown')}: {e}")
            # If we can't parse the date, include it to be safe
            filtered_events.append(event)
    
    # Deduplicate events (same title and date)
    seen_events = set()
    deduplicated_events = []
    for event in filtered_events:
        event_key = (event.get("title", "").strip().lower(), event.get("start", ""))
        if event_key not in seen_events:
            seen_events.add(event_key)
            deduplicated_events.append(event)
        else:
            print(f"Deduplicating event: {event.get('title', 'Unknown')} on {event.get('start', 'Unknown')}")
    
    print(f"Total events found for {url}: {len(events)}, after filtering past events: {len(filtered_events)}, after deduplication: {len(deduplicated_events)}")
    return deduplicated_events

# -----------------------------
# Generate events endpoint
# -----------------------------
@app.post("/generate_events")
def generate_events(request: QueryRequest):
    try:
        user_query = request.query.strip()
        all_events = []
        attractions = []

        # Step 1: scrape approved sites
        for site in APPROVED_SITES:
            if "wanderlog.com" in site or "exploregeorgia.org" in site or "tripadvisor.com" in site:
                # Handle these sites as attractions
                site_attractions = scrape_site(site)
                attractions.extend(site_attractions)
            else:
                # Handle other sites as events
                events = scrape_site(site)
                all_events.extend(events)

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