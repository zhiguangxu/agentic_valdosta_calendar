"""Check content after removing nav/footer/header"""
import requests
from bs4 import BeautifulSoup

url = "https://www.valdosta.edu/colleges/arts/music/concert-calendar.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Remove unnecessary elements (same as scraper)
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

# Check body after cleanup
body = soup.find("body")
if body:
    body_text = body.get_text()
    print(f"Body text after cleanup length: {len(body_text)}")
    print(f"'February' in body after cleanup: {'February' in body_text}")
    
    # Get HTML
    body_html = str(body)
    print(f"Body HTML after cleanup length: {len(body_html)}")
    print(f"'February' in body HTML: {'February' in body_html}")
    
    if 'February' in body_html:
        idx = body_html.find('February')
        print(f"\nHTML context around 'February':")
        print(body_html[max(0, idx-200):idx+500])

# Check main content
main_content = soup.find(["main", "article"]) or soup.find("div", class_=lambda x: x and ("main" in str(x).lower() or "content" in str(x).lower()))
if main_content:
    print(f"\n\nMain content found, length: {len(str(main_content))}")
    print(f"'February' in main_content: {'February' in str(main_content)}")
else:
    print("\n\nNo main_content found")
