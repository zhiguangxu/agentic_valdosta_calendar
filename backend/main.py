import os
import requests
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI

# -----------------------------
# Setup
# -----------------------------
app = FastAPI()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

# Detect mode: LOCAL for dev, HF for Hugging Face deploy
MODE = os.environ.get("ENV", "LOCAL")

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
else:  # HF deploy
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
# Serper search helper
# -----------------------------
def search_serper(query: str):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query}
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()

# -----------------------------
# Generate events endpoint
# -----------------------------
@app.post("/generate_events")
def generate_events(request: QueryRequest):
    try:
        user_query = request.query.strip()

        # ✅ Step 1: approved websites
        approved_sites = [
            "https://visitvaldosta.org/events/",
            "https://www.valdostamainstreet.com/events-calendar",
            "https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta",
            "https://exploregeorgia.org/article/guide-to-valdosta",
            "https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html"
        ]

        # ✅ Step 2: Ask GPT to generate site-specific Serper queries
        site_query_prompt = f"""
        You are an assistant that receives a user search query and a list of websites.
        Generate one Google-style search query per website, using the user query.
        List the queries in plain text, one per line.
        User query: "{user_query}"
        Websites: {json.dumps(approved_sites)}
        """
        query_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": site_query_prompt}]
        )

        raw_queries = query_response.choices[0].message.content.strip().splitlines()
        search_queries = [q.strip() for q in raw_queries if q.strip()]

        # ✅ Step 3: Run Serper for each site-specific query
        serper_results = []
        for q in search_queries:
            try:
                res = search_serper(q)
                serper_results += res.get("organic", [])
            except Exception as e:
                print(f"Serper query failed: {q}, error: {e}")

        # ✅ Step 4: Feed Serper results into GPT for structured events
        context = json.dumps(serper_results, indent=2)

        system_prompt = """
        You are an assistant that extracts events from web search results.
        Input: JSON of search results (title, snippet, link).
        Output: JSON array of events, each with:
        - title (string)
        - date (YYYY-MM-DD if available, else guess a near-future date)
        - time (HH:MM or default "12:00")
        - url (string)
        - description (string, short summary)
        Always output valid JSON only, no extra text.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ]
        )

        raw_output = response.choices[0].message.content.strip()
        if raw_output.startswith("```json"):
            raw_output = raw_output[len("```json"):].strip()
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3].strip()

        events = json.loads(raw_output)

        # ✅ Return for frontend
        return {"events": events}

    except Exception as e:
        return {"error": str(e)}
