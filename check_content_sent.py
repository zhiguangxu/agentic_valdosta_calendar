"""Check what content is actually sent to AI"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {"User-Agent": "Mozilla/5.0"}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Clean up
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

html_content = str(soup.body)[:30000] if soup.body else ""

print(f"Content length: {len(html_content)}")
print(f"\nChecking for event indicators in first 30000 chars:")
print(f"  'February' found: {'February' in html_content}")
print(f"  'Concert' found: {'Concert' in html_content}")
print(f"  'February 17' found: {'February 17' in html_content}")
print(f"  'February 22' found: {'February 22' in html_content}")

if 'February' in html_content:
    # Find last occurrence to see how far we got
    last_idx = html_content.rfind('February')
    context = html_content[max(0, last_idx-100):last_idx+200]
    print(f"\nLast 'February' at position {last_idx}:")
    print(context)
