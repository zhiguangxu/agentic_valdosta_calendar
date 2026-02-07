"""Test Turner Center classes scraping"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import generic_scraper
import requests
from bs4 import BeautifulSoup

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

url = "https://turnercenter.org/classes"
print(f"Testing: {url}")
print("="*80)

# First, let's see what's on the page
headers = {"User-Agent": "Mozilla/5.0"}
try:
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Get page title
    page_title = soup.title.string if soup.title else "No title"
    print(f"Page title: {page_title}")

    # Remove scripts/styles
    for elem in soup(['script', 'style']):
        elem.decompose()

    # Get text content
    text = soup.get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    print(f"\nPage content preview (first 30 lines with keywords):")
    count = 0
    for i, line in enumerate(lines):
        if any(word in line.lower() for word in ['class', 'course', 'workshop', 'lesson', 'art', 'pottery', 'paint', 'draw', 'dance', 'music', 'january', 'february', 'march', '2026', 'day', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            print(f"{i}: {line[:120]}")
            count += 1
            if count >= 30:
                break

    print("\n" + "="*80)
    print("\nNow testing two-stage scraping with AI...")
    print("="*80)

    if client:
        classes = generic_scraper.scrape_with_ai(url, 'classes', client, 'ai_twostage')
        print(f"\nExtracted {len(classes)} classes:")

        if classes:
            # Group by month
            from collections import defaultdict
            by_month = defaultdict(list)
            for cls in classes:
                month = cls['start'][:7]  # YYYY-MM
                by_month[month].append(cls)

            for month in sorted(by_month.keys()):
                print(f"\n{month}: {len(by_month[month])} class(es)")
                for cls in by_month[month]:
                    print(f"  - {cls['title']} on {cls['start'].split('T')[0]}")
                    if cls.get('description'):
                        print(f"    {cls['description'][:100]}...")
                    if cls.get('url'):
                        print(f"    URL: {cls['url']}")
        else:
            print("No classes found. This could mean:")
            print("1. The page has no classes listed")
            print("2. The page structure is different than expected")
            print("3. All classes are in the past")
    else:
        print("OpenAI client not available")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
