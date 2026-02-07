"""Extract VSU events with context"""
import requests
from bs4 import BeautifulSoup
import re

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Remove scripts, styles, nav, footer, header
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

# Get all text
text = soup.get_text()
lines = [line.strip() for line in text.split('\n') if line.strip()]

# Find lines with dates and get context
date_pattern = re.compile(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+', re.IGNORECASE)

print("Events with dates:\n")
for i, line in enumerate(lines):
    if date_pattern.search(line):
        # Get context: 2 lines before and 3 lines after
        context_before = lines[max(0, i-2):i]
        context_after = lines[i+1:min(len(lines), i+4)]
        
        print(f"Date: {line}")
        if context_before:
            print(f"  Before: {' | '.join(context_before)}")
        if context_after:
            print(f"  After: {' | '.join(context_after)}")
        print()
