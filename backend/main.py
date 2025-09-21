# backend/main.py
import os
import requests
import json
from datetime import datetime, timedelta
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
# Scraping function with description extraction
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

    for idx, a in enumerate(soup.find_all("a", href=True)):
        text = a.get_text(strip=True)
        link = a["href"]

        if not text or len(text) < 3 or link.startswith("tel:") or link.startswith("mailto:"):
            continue

        keywords = ["event", "festival", "concert", "show", "tour", "attraction", "art", "music"]
        if any(kw in text.lower() for kw in keywords) or any(kw in link.lower() for kw in keywords):
            if link.startswith("/"):
                link = urljoin(url, link)

            # Extract description: look for nearby <p> or <div> with text
            description = ""
            parent = a.find_parent()
            if parent:
                # Find first <p> in parent
                p = parent.find("p")
                if p:
                    description = p.get_text(strip=True)
                else:
                    # fallback: get next sibling text
                    next_sib = a.find_next_sibling()
                    if next_sib:
                        description = next_sib.get_text(strip=True)

            # Deterministic date/time
            date_str = (datetime.today() + timedelta(days=idx)).strftime("%Y-%m-%d")
            time_choices = ["10:00", "14:00", "18:00"]
            time_str = time_choices[idx % len(time_choices)]

            events.append({
                "title": text,
                "url": link,
                "description": description,
                "date": date_str,
                "time": time_str,
                "start": f"{date_str}T{time_str}:00"
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
            system_prompt = f"""
            You are an assistant that generates events from a user query.
            User query: "{user_query}"
            Output: JSON array of events, each with:
            - title (string)
            - date (YYYY-MM-DD)
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
                # Deterministic date/time for GPT fallback events
                for idx, ev in enumerate(gpt_events):
                    date_str = (datetime.today() + timedelta(days=len(all_events) + idx)).strftime("%Y-%m-%d")
                    time_choices = ["10:00", "14:00", "18:00"]
                    time_str = time_choices[(len(all_events) + idx) % len(time_choices)]
                    ev["date"] = date_str
                    ev["time"] = time_str
                    ev["start"] = f"{date_str}T{time_str}:00"
                    ev["description"] = ev.get("description", "")
                    ev["url"] = ev.get("url", "")
                all_events.extend(gpt_events)
            except Exception as e:
                print(f"Failed to parse GPT events: {e}")

        return {"events": all_events}

    except Exception as e:
        return {"error": str(e)}
