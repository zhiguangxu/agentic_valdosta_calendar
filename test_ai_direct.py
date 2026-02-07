"""Test AI directly on VSU content"""
import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {"User-Agent": "Mozilla/5.0"}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Clean up
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

html_content = str(soup.body)[:30000] if soup.body else ""

prompt = """Extract event information from this concert calendar page. For each event, extract:
1. The event title
2. The URL (if available, otherwise empty string "")
3. The date (YYYY-MM-DD format)
4. The time (HH:MM 24-hour format)

Look for patterns like:
- "Day, Month Date" followed by event titles
- "Event Title | Time | Venue"

Only extract events after February 7, 2026.
Use year 2026 for all dates.

Return JSON array: [{"title": "...", "url": "", "date": "...", "time": "..."}]
"""

print("Sending to AI...")
print(f"HTML length: {len(html_content)}")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt + "\n\nHTML:\n" + html_content}],
    temperature=0.1
)

result = response.choices[0].message.content
print(f"\nAI Response:\n{result}")
