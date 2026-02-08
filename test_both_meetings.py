#!/usr/bin/env python3
"""
Test scraping BOTH meeting sources to see where inconsistency comes from.
"""
import sys
sys.path.insert(0, 'backend')

from backend import generic_scraper
from backend.main import deduplicate_meetings
from openai import OpenAI
import os

# Load API key
from dotenv import load_dotenv
load_dotenv('backend/.env')

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

sources = [
    {
        "name": "City of Valdosta",
        "url": "https://www.valdostacity.com/city-council/agendas-minutes",
        "type": "meetings"
    },
    {
        "name": "Lowndes County Board of Commissioners",
        "url": "https://lowndescounty.com/calendar.aspx?CID=23&Keywords=&startDate=&enddate=&",
        "type": "meetings"
    }
]

print("="*80)
print("TESTING BOTH MEETING SOURCES")
print("="*80)

for attempt in range(1, 4):
    print(f"\n{'='*80}")
    print(f"ATTEMPT {attempt}")
    print(f"{'='*80}")

    all_meetings = []

    for source in sources:
        print(f"\n[{source['name']}] Scraping...")
        meetings = generic_scraper.scrape_with_ai(source['url'], 'meetings', client, "ai_twostage")

        # Add source field to each meeting
        for m in meetings:
            m['source'] = source['name']

        print(f"[{source['name']}] Found {len(meetings)} meetings")
        for m in meetings:
            print(f"  - {m.get('title', 'N/A')[:60]} on {m.get('start', 'N/A')}")

        all_meetings.extend(meetings)

    print(f"\n{'='*80}")
    print(f"Before deduplication: {len(all_meetings)} total meetings")
    print(f"{'='*80}")

    # Deduplicate
    unique_meetings = deduplicate_meetings(all_meetings)

    print(f"\n{'='*80}")
    print(f"After deduplication: {len(unique_meetings)} unique meetings")
    print(f"{'='*80}")

    # Show all unique meetings
    print("\nFinal meeting list:")
    for i, m in enumerate(sorted(unique_meetings, key=lambda x: x.get('start', '')), 1):
        source_name = m.get('source', 'Unknown')
        title = m.get('title', 'N/A')
        date = m.get('start', 'N/A')
        print(f"  {i}. [{source_name}] {title[:60]} - {date}")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print("Check if counts are consistent across all 3 attempts above.")
