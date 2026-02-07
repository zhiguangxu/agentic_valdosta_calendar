"""
Check the actual HTML structure to parse it properly
"""
import requests
from bs4 import BeautifulSoup

url = "https://visitvaldosta.org/events/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Find event containers
containers = soup.find_all(["article", "div", "li"], class_=lambda x: x and "event" in x.lower() if x else False, limit=5)

print(f"Found {len(containers)} event containers\n")
print("="*80)

for i, container in enumerate(containers[:5], 1):
    print(f"\nEVENT {i}:")
    print("HTML structure:")
    print(container.prettify()[:800])
    print("="*80)
