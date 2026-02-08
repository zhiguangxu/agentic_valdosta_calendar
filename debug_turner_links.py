#!/usr/bin/env python3
"""Check if individual classes have separate URLs"""

import requests
from bs4 import BeautifulSoup

url = "https://turnercenter.org/drawing_mixedmedia_2d_education/"

print(f"Fetching: {url}")
print("="*60)

resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

print("\n📋 Class Structure:")
print()

# Find the category name
category = None
for h4 in soup.find_all('h4'):
    text = h4.get_text(strip=True)
    if '|' in text or text.isupper():
        category = text
        print(f"Category: {category}")
        break

print("\nIndividual Classes:")
print()

# Find all H4 headings (these are class names)
for h4 in soup.find_all('h4'):
    text = h4.get_text(strip=True)

    # Skip the category heading
    if text == category:
        continue

    # Check if this H4 has a link inside or nearby
    link = h4.find('a')
    if not link:
        # Check parent
        parent = h4.parent
        if parent:
            link = parent.find('a')

    if link and link.get('href'):
        print(f"  ✓ {text}")
        print(f"    URL: {link.get('href')}")
    else:
        print(f"  ✗ {text}")
        print(f"    No separate URL - content on this page only")
    print()
