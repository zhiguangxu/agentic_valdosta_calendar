"""Check if March events are in the 60k chars"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {"User-Agent": "Mozilla/5.0"}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Clean up
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

html_content = str(soup.body)[:60000] if soup.body else ""

print(f"Content length: {len(html_content)}")
print(f"'March' in first 60000 chars: {'March' in html_content}")
print(f"'April' in first 60000 chars: {'April' in html_content}")

if 'March' in html_content:
    # Count March dates
    import re
    march_dates = re.findall(r'(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+March\s+\d+', html_content)
    print(f"\nFound {len(march_dates)} March dates in first 60k chars")
    for date in march_dates[:10]:
        print(f"  - {date}")
else:
    print("\nMarch content is NOT in first 60,000 chars")

# Check full body length
full_body = str(soup.body) if soup.body else ""
print(f"\nFull body length: {len(full_body)}")
print(f"'March' in full body: {'March' in full_body}")

if 'March' in full_body:
    march_idx = full_body.find('March')
    print(f"First 'March' appears at position: {march_idx}")
