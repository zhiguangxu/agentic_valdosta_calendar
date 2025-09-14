import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import OpenAI

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    # allow_origins=["*"],  # On HF, you want wide access
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

@app.post("/generate_events")
async def generate_events(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "Sample events")

    system_message = """
    You are an assistant that outputs a JSON array of events.
    ONLY use these sources when generating events:
    - https://visitvaldosta.org/events/
    - https://www.valdostamainstreet.com/events-calendar
    - https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta
    - https://exploregeorgia.org/article/guide-to-valdosta
    - https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html

    Each event must have:
      - title (string)
      - date (YYYY-MM-DD)
      - time (HH:MM)
    Each even should also include the url field, which is a link to more info about the event.
    Each event should also include the description field, which is a description of the event.
    Always return JSON, no extra text.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
        )

        raw_output = response.choices[0].message.content.strip()

        if raw_output.startswith("```json"):
            raw_output = raw_output[len("```json"):].strip()
        if raw_output.startswith("```"):
            raw_output = raw_output[3:].strip()
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3].strip()

        events = json.loads(raw_output)
    except Exception as e:
        print("Error parsing GPT output:", e)
        events = []

    print("Events:", events)

    clean_events = []
    for e in events:
        date = e.get("date", "2025-09-20")
        time = e.get("time", "12:00")
        url = e.get("url", "#")  # default to "#" if no link provided
        description = e.get("description", "No description available.")
        clean_events.append({
            "title": e.get("title", "Untitled Event"),
            "start": f"{date}T{time}:00",
            "url": url,
            "extendedProps": {
            "description": description
        }
        })

    print("Clean events:", clean_events)

    return {"events": clean_events}


# === Serve React build ===
app.mount("/static", StaticFiles(directory="backend/static/static"), name="static")

@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    return FileResponse("backend/static/index.html")
