"""Check raw HTML before cleaning"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)

# Check raw HTML
print(f"Raw HTML length: {len(resp.text)}")
print(f"'February' in raw HTML: {'February' in resp.text}")
print(f"'Concert' in raw HTML: {'Concert' in resp.text}")

# Parse and check body WITHOUT removing elements
soup = BeautifulSoup(resp.text, "html.parser")
body = soup.find("body")

if body:
    body_text = body.get_text()
    print(f"\nBody text length: {len(body_text)}")
    print(f"'February' in body text: {'February' in body_text}")
    
    # Find where February appears
    if 'February' in body_text:
        idx = body_text.find('February')
        print(f"\nContext around first 'February':")
        print(body_text[max(0, idx-100):idx+300])

# Check if content is in specific divs
print("\nLooking for content containers...")
content_divs = soup.find_all("div", id=True)
for div in content_divs[:10]:
    div_id = div.get('id', '')
    text = div.get_text()[:200]
    if 'february' in text.lower() or 'concert' in text.lower():
        print(f"\n  Found in div#{div_id}:")
        print(f"    {text}")
