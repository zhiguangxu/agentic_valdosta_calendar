"""Debug what AI receives for VSU"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Remove unnecessary elements (same as scraper does)
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

# Get main content
main_content = soup.find(["main", "article"]) or soup.find("div", class_=lambda x: x and ("main" in str(x).lower() or "content" in str(x).lower()))

if main_content:
    html_content = str(main_content)[:30000]
else:
    html_content = str(soup.body)[:30000] if soup.body else str(soup)[:30000]

print(f"HTML content length: {len(html_content)}")
print("\nFirst 3000 chars of HTML content sent to AI:")
print("="*80)
print(html_content[:3000])
print("="*80)
print("\nSearching for 'February' in content...")
if 'February' in html_content:
    print("✓ Found 'February'")
    # Find snippet around February
    idx = html_content.find('February')
    print(f"\nContext around 'February':")
    print(html_content[max(0, idx-200):idx+500])
else:
    print("✗ 'February' NOT found in HTML content")
