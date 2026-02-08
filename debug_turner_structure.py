#!/usr/bin/env python3
"""Debug: Check Turner Center page structure for class naming"""

import requests
from bs4 import BeautifulSoup

# Check the drawing/mixed media page structure
url = "https://turnercenter.org/drawing_mixedmedia_2d_education/"

print(f"Fetching: {url}")
print("="*60)

resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

# Look for headings and class names
print("\n📋 All Headings:")
for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    text = heading.get_text(strip=True)
    if text and len(text) < 200:
        print(f"  {heading.name.upper()}: {text}")

print("\n" + "="*60)

# Check another page - Active Arts
url2 = "https://turnercenter.org/activearts_education/"
print(f"\nFetching: {url2}")
print("="*60)

resp2 = requests.get(url2)
soup2 = BeautifulSoup(resp2.text, "html.parser")

print("\n📋 All Headings:")
for heading in soup2.find_all(['h1', 'h2', 'h3', 'h4']):
    text = heading.get_text(strip=True)
    if text and len(text) < 200:
        print(f"  {heading.name.upper()}: {text}")
