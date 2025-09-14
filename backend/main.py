from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os, json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI()

# Allow frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/generate_events")
def generate_events(req: PromptRequest):
    system_message = """
    You are an assistant that outputs a JSON array of events.
    Each event must have:
      - title (string)
      - date (YYYY-MM-DD)
      - time (HH:MM)
    Return only JSON.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":system_message},
                {"role":"user","content":req.prompt}
            ]
        )
        raw_output = response.choices[0].message.content.strip()
        # Remove ``` blocks
        if raw_output.startswith("```json"): raw_output = raw_output[7:].strip()
        if raw_output.startswith("```"): raw_output = raw_output[3:].strip()
        if raw_output.endswith("```"): raw_output = raw_output[:-3].strip()

        events = json.loads(raw_output)
    except Exception as e:
        print("Error:", e)
        events = [
            {"title":"Sample Event 1","date":"2025-09-15","time":"10:00"},
            {"title":"Sample Event 2","date":"2025-09-18","time":"15:00"}
        ]

    # Convert to FullCalendar format
    fc_events = []
    for e in events:
        date = e.get("date", "2025-09-20")
        time = e.get("time", "12:00")
        fc_events.append({
            "title": e.get("title", "Untitled"),
            "start": f"{date}T{time}:00"
        })

    print("FullCalendar events:", fc_events)

    return {"events": fc_events}
