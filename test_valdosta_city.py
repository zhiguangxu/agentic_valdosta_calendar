"""
Test the valdostacity.com/calendar structure
"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdostacity.com/calendar"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

print(f"Status: {resp.status_code}")
print(f"Page title: {soup.title.string if soup.title else 'No title'}")
print("\n" + "="*80)

# Check for calendar table
table = soup.find("table")
if table:
    print("✓ Found calendar table")
    # Get a few event cells
    cells = table.find_all("td", attrs={"data-date": True}, limit=5)
    print(f"✓ Found {len(cells)} cells with data-date")

    for cell in cells[:3]:
        date = cell.get("data-date")
        links = cell.find_all("a", href=True)
        print(f"\nDate: {date}")
        for link in links[:2]:
            print(f"  Event: {link.get_text(strip=True)}")
            print(f"  URL: {link.get('href')}")
else:
    print("✗ No calendar table found")
    # Check for other structures
    containers = soup.find_all(["article", "div"], class_=lambda x: x and "event" in x.lower() if x else False, limit=5)
    print(f"Found {len(containers)} event containers")
