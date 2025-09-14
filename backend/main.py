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
    Each event must have:
      - title (string)
      - date (YYYY-MM-DD)
      - time (HH:MM)
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

    clean_events = []
    for e in events:
        date = e.get("date", "2025-09-20")
        time = e.get("time", "12:00")
        clean_events.append({
            "title": e.get("title", "Untitled Event"),
            "start": f"{date}T{time}:00"
        })

    return {"events": clean_events}


# === Serve React build ===
app.mount("/static", StaticFiles(directory="backend/static/static"), name="static")

@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    return FileResponse("backend/static/index.html")
