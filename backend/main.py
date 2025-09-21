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
]

# -----------------------------
# Scraping function with real date extraction
# -----------------------------
def scrape_site(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
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
                
                # Extract description
                desc_elem = article.find("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Extract URL from parent link
                parent_link = article.find_parent("a")
                event_url = ""
                if parent_link and parent_link.get("href"):
                    event_url = parent_link["href"]
                    if event_url.startswith("/"):
                        event_url = urljoin(url, event_url)
                
                events.append({
                    "title": title,
                    "url": event_url,
                    "description": description,
                    "start": f"{date_str}T12:00:00",
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing event article: {e}")
                continue
    
    # Handle valdostamainstreet.com structure (fallback to generic scraping)
    else:
        # Look for common event patterns
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            link = a["href"]

            if not text or len(text) < 3 or link.startswith("tel:") or link.startswith("mailto:"):
                continue

            keywords = ["event", "festival", "concert", "show", "tour", "attraction", "art", "music", "calendar"]
            if not any(kw in text.lower() for kw in keywords) and not any(kw in link.lower() for kw in keywords):
                continue

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

            # Extract date - look for various date patterns
            date_str = None
            time_str = "12:00"
            
            # Check <time> tag
            time_tag = a.find("time")
            if time_tag and time_tag.has_attr("datetime"):
                date_str = time_tag["datetime"].split("T")[0]
            
            # Check parent text for date-like patterns
            if not date_str and parent:
                # Look for various date formats
                date_patterns = [
                    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
                    r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                    r'\b\d{4}-\d{2}-\d{2}\b',
                    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, parent.get_text())
                    if match:
                        try:
                            dt = dateparser.parse(match.group())
                            if dt:
                                date_str = dt.strftime("%Y-%m-%d")
                                break
                        except:
                            continue
            
            # Skip event if no date found
            if not date_str:
                continue

            events.append({
                "title": text,
                "url": link,
                "description": description,
                "start": f"{date_str}T{time_str}:00",
                "allDay": False
            })

    return events

# -----------------------------
# Generate events endpoint
# -----------------------------
@app.post("/generate_events")
def generate_events(request: QueryRequest):
    try:
        user_query = request.query.strip()
        all_events = []

        # Step 1: scrape approved sites
        for site in APPROVED_SITES:
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

        return {"events": all_events}

    except Exception as e:
        return {"error": str(e)}
