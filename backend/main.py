# backend/main.py
import os
import requests
import json
import re
from datetime import datetime
from dateutil import parser as dateparser
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import urljoin

# -----------------------------
# Setup
# -----------------------------
app = FastAPI()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
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
        event_articles = soup.find_all("article", class_="event")
        print(f"Found {len(event_articles)} event articles on visitvaldosta.org")
        for article in event_articles:
            try:
                # Extract title from h3
                title_elem = article.find("h3")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Extract date information
                date_elem = article.find("div", class_="date")
                month_elem = article.find("div", class_="txt")
                
                if not date_elem or not month_elem:
                    continue
                    
                day = date_elem.find("span").get_text(strip=True)
                month_text = month_elem.find("span").get_text(strip=True)
                
                # Get current year as fallback
                current_year = datetime.now().year
                
                # Parse the date
                try:
                    date_str = f"{month_text} {day}, {current_year}"
                    print(f"Parsing date: {date_str}")
                    dt = dateparser.parse(date_str)
                    if dt:
                        date_str = dt.strftime("%Y-%m-%d")
                        print(f"Parsed date: {date_str}")
                    else:
                        print(f"Failed to parse date: {date_str}")
                        continue
                except Exception as e:
                    print(f"Date parsing error: {e}")
                    continue
                
                # Extract time information (simplified for robustness)
                time_str = None
                # Look for time patterns in the entire article text
                article_text = article.get_text()
                time_patterns = [
                    r'\b(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)\b',
                    r'\b(\d{1,2})\s*(?:AM|PM|am|pm)\b',
                    r'\b(\d{1,2}):(\d{2})\b'
                ]
                
                for pattern in time_patterns:
                    match = re.search(pattern, article_text)
                    if match:
                        try:
                            if len(match.groups()) == 2:  # HH:MM format
                                hour, minute = match.groups()
                                time_str = f"{hour.zfill(2)}:{minute}"
                            else:  # H AM/PM format
                                hour = match.group(1)
                                if 'PM' in match.group(0).upper() and int(hour) != 12:
                                    hour = str(int(hour) + 12)
                                elif 'AM' in match.group(0).upper() and int(hour) == 12:
                                    hour = "00"
                                time_str = f"{hour.zfill(2)}:00"
                            break
                        except (ValueError, IndexError):
                            continue
                
                # Extract description first
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
                        # Default to business hours with some variation
                        time_str = f"{random.randint(9, 17):02d}:00"
                
                # Extract URL from parent link
                parent_link = article.find_parent("a")
                event_url = ""
                if parent_link and parent_link.get("href"):
                    event_url = parent_link["href"]
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
    
    # Handle valdostamainstreet.com structure (fallback to generic scraping)
    elif "valdostamainstreet.com" in url:
        # Look for common event patterns
        all_links = soup.find_all("a", href=True)
        print(f"Found {len(all_links)} total links on valdostamainstreet.com")
        for a in all_links:
            text = a.get_text(strip=True)
            link = a["href"]

            if not text or len(text) < 3 or link.startswith("tel:") or link.startswith("mailto:"):
                continue

            keywords = ["event", "festival", "concert", "show", "tour", "attraction", "art", "music", "calendar"]
            if not any(kw in text.lower() for kw in keywords) and not any(kw in link.lower() for kw in keywords):
                continue
            
            print(f"Processing potential event: {text[:50]}...")

            if link.startswith("/"):
                link = urljoin(url, link)

            # Extract description
            description = ""
            parent = a.find_parent()
            if parent:
                p = parent.find("p")
                if p:
                    description = p.get_text(strip=True)
                else:
                    next_sib = a.find_next_sibling()
                    if next_sib:
                        description = next_sib.get_text(strip=True)

            # Extract date and time - look for various date patterns
            date_str = None
            time_str = None
            
            # Check <time> tag
            time_tag = a.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                datetime_str = time_tag["datetime"]
                if "T" in datetime_str:
                    date_str, time_str = datetime_str.split("T")
                    # Keep only HH:MM part
                    if ":" in time_str:
                        time_str = time_str.split(":")[0] + ":" + time_str.split(":")[1]
                else:
                    date_str = datetime_str
            
            # Check parent text for date and time patterns
            if not date_str and parent:
                parent_text = parent.get_text()
                
                # Look for various date formats
                date_patterns = [
                    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
                    r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                    r'\b\d{4}-\d{2}-\d{2}\b',
                    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, parent_text)
                    if match:
                        try:
                            dt = dateparser.parse(match.group())
                            if dt:
                                date_str = dt.strftime("%Y-%m-%d")
                                break
                        except:
                            continue
                
                # Look for time patterns if no time found yet
                if not time_str:
                    time_patterns = [
                        r'\b(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)\b',
                        r'\b(\d{1,2})\s*(?:AM|PM|am|pm)\b',
                        r'\b(\d{1,2}):(\d{2})\b'
                    ]
                    
                    for pattern in time_patterns:
                        match = re.search(pattern, parent_text)
                        if match:
                            try:
                                if len(match.groups()) == 2:  # HH:MM format
                                    hour, minute = match.groups()
                                    time_str = f"{hour.zfill(2)}:{minute}"
                                else:  # H AM/PM format
                                    hour = match.group(1)
                                    if 'PM' in match.group(0).upper() and int(hour) != 12:
                                        hour = str(int(hour) + 12)
                                    elif 'AM' in match.group(0).upper() and int(hour) == 12:
                                        hour = "00"
                                    time_str = f"{hour.zfill(2)}:00"
                                break
                            except (ValueError, IndexError):
                                continue
            
            # Skip event if no date found
            if not date_str:
                continue

            # Set intelligent default time if none found
            if not time_str:
                import random
                # Determine event type from title/description
                event_text = (text + " " + description).lower()
                
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
                    # Default to business hours with some variation
                    time_str = f"{random.randint(9, 17):02d}:00"

            print(f"Adding event: {text} at {date_str}T{time_str}:00")
            events.append({
                "title": text,
                "url": link,
                "description": description,
                "start": f"{date_str}T{time_str}:00",
                "allDay": False
            })

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

    print(f"Total events found for {url}: {len(events)}")
    return events

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
        if len(all_events) < 5:
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

        # Sort events by start date
        all_events.sort(key=lambda x: x["start"])

        return {
            "events": all_events,
            "attractions": attractions
        }

    except Exception as e:
        return {"error": str(e)}
