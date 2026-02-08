#!/usr/bin/env python3
"""Debug: Check Turner Center drawing class page"""

import requests
from bs4 import BeautifulSoup

url = "https://turnercenter.org/drawing-fiber-art-mixed-media/"

print(f"Fetching: {url}")
print("="*60)

resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

# Look for date/time information
print("\n📅 Date/Time Info:")
for text in soup.stripped_strings:
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ['saturday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'sunday', 'pm', 'am', '2nd', 'second', 'every', 'weekly', 'month']):
        print(f"  {text}")

print("\n" + "="*60)
