"""Check Presenter Series page dates"""
import requests
from bs4 import BeautifulSoup

url = "https://turnercenter.org/presenter-series/"
headers = {"User-Agent": "Mozilla/5.0"}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Get text
    text = soup.get_text()
    
    # Look for date patterns
    import re
    dates = re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s+\d{4}', text, re.IGNORECASE)
    
    print(f"Found dates with years:")
    for date in dates[:10]:
        print(f"  - {date}")
    
    # Look for dates without years
    dates_no_year = re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+(?!,?\s+\d{4})', text, re.IGNORECASE)
    
    print(f"\nFound dates without years (first 10):")
    for date in dates_no_year[:10]:
        print(f"  - {date}")
        
except Exception as e:
    print(f"Error: {e}")
