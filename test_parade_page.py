"""Check what date is actually on the Black History Month Parade page"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdostacity.com/event/2nd-annual-black-history-month-parade"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Remove scripts and styles
for element in soup(["script", "style"]):
    element.decompose()

# Get text content
text = soup.get_text()

# Find lines with date keywords
lines = text.split('\n')
for i, line in enumerate(lines):
    line_lower = line.lower()
    if any(keyword in line_lower for keyword in ['february', 'feb', '2026', 'date', 'when', 'friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday']):
        if line.strip():
            print(line.strip())
