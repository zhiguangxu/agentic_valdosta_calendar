"""
Check what the listing page actually shows
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

url = "https://visitvaldosta.org/events/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Find all event entries
events = soup.find_all(["article", "div", "li"], class_=lambda x: x and "event" in x.lower() if x else False, limit=50)

print(f"Found {len(events)} event containers\n")
print("="*80)

# Check for specific events
target_events = [
    "Black History Month Parade",
    "Unmask the Night",
    "South Georgia Film Festival",
    "Wildflower Cafe",
    "Valentine's"
]

for event in events[:30]:  # Check first 30
    text = event.get_text(strip=True)[:200]

    # Check if any target event is mentioned
    for target in target_events:
        if target.lower() in text.lower():
            print(f"\nFound: {target}")
            print(f"Text: {text}")

            # Find date
            date_elem = event.find(["time", "span", "div"], class_=lambda x: x and ("date" in x.lower() or "time" in x.lower()) if x else False)
            if date_elem:
                print(f"Date element: {date_elem.get_text(strip=True)}")

            # Find link
            link = event.find("a", href=True)
            if link:
                print(f"URL: {link.get('href')}")

            print("-"*80)
            break
