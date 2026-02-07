"""Check VSU page structure in detail"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Check for iframes
iframes = soup.find_all("iframe")
print(f"Found {len(iframes)} iframes")
for iframe in iframes:
    print(f"  - src: {iframe.get('src', 'No src')}")

# Check for calendar/event containers
print("\nLooking for event containers...")
tables = soup.find_all("table")
print(f"Found {len(tables)} tables")

# Look for divs with event-related classes
event_divs = soup.find_all("div", class_=lambda x: x and any(word in str(x).lower() for word in ["event", "concert", "calendar"]))
print(f"Found {len(event_divs)} divs with event-related classes")

# Check if content is in body
body = soup.find("body")
if body:
    # Get text that contains "February" or "March"
    text = body.get_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    print("\nLines containing 'February' or 'March' (first 20):")
    count = 0
    for line in lines:
        if 'february' in line.lower() or 'march' in line.lower():
            print(f"  {line[:100]}")
            count += 1
            if count >= 20:
                break

# Check for calendar widget or embedded content
print("\nLooking for calendar indicators...")
calendar_elements = soup.find_all(class_=lambda x: x and "calendar" in str(x).lower())
print(f"Found {len(calendar_elements)} elements with 'calendar' in class")
