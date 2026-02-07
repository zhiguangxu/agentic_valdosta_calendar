"""Check VSU page content"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

soup = BeautifulSoup(resp.text, "html.parser")

# Remove scripts and styles
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

# Get main content
main_content = soup.find(["main", "article"]) or soup.find("div", class_=lambda x: x and ("main" in x.lower() or "content" in x.lower()))

if main_content:
    text = main_content.get_text()[:2000]
    print(f"\nMain content preview:\n{text}")
else:
    # Get body text
    text = soup.body.get_text()[:2000] if soup.body else soup.get_text()[:2000]
    print(f"\nBody text preview:\n{text}")

# Look for event indicators
print("\n" + "="*80)
print("Looking for event indicators...")
event_keywords = ["concert", "performance", "event", "date", "time", "february", "march"]
for keyword in event_keywords:
    count = resp.text.lower().count(keyword)
    if count > 0:
        print(f"  '{keyword}': {count} occurrences")
