"""Check what's actually on the Presenter Series page"""
import requests
from bs4 import BeautifulSoup

url = "https://turnercenter.org/presenter-series/"
headers = {"User-Agent": "Mozilla/5.0"}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Remove scripts/styles
    for elem in soup(["script", "style"]):
        elem.decompose()
    
    text = soup.get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    print("Page content (showing lines with keywords):")
    for i, line in enumerate(lines):
        if any(word in line.lower() for word in ['february', 'march', 'january', '2025', '2026', 'date', 'show']):
            print(f"{i}: {line[:120]}")
            
except Exception as e:
    print(f"Error: {e}")
