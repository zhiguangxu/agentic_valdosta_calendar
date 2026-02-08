#!/usr/bin/env python3
"""
Test the full flow including deduplication to see if that's where inconsistency comes from.
"""
import sys
sys.path.insert(0, 'backend')

from backend import source_manager, generic_scraper
from backend.main import deduplicate_meetings
from openai import OpenAI
import os

# Load API key
from dotenv import load_dotenv
load_dotenv('backend/.env')

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

print("="*80)
print("TESTING FULL MEETING SCRAPING FLOW")
print("="*80)

# Get meetings sources
sources = source_manager.get_sources_by_type('meetings')
print(f"\nFound {len(sources)} meeting sources:")
for source in sources:
    print(f"  - {source['name']}: {source['url']}")

# Run full flow 3 times
for attempt in range(1, 4):
    print(f"\n{'='*80}")
    print(f"ATTEMPT {attempt}: FULL FLOW")
    print(f"{'='*80}")

    all_meetings = []

    # Scrape each source
    for source in sources:
        print(f"\nScraping: {source['name']}")
        meetings = generic_scraper.scrape_with_ai(source['url'], 'meetings', client, "ai_twostage")
        print(f"  Found: {len(meetings)} meetings")
        all_meetings.extend(meetings)

    print(f"\nTotal meetings before deduplication: {len(all_meetings)}")

    # Deduplicate
    unique_meetings = deduplicate_meetings(all_meetings)
    print(f"Total meetings after deduplication: {len(unique_meetings)}")

    # Filter by source
    lowndes_meetings = [m for m in unique_meetings if 'Lowndes County' in m.get('source', '')]
    print(f"Lowndes County meetings: {len(lowndes_meetings)}")

    print("\nFinal meeting list:")
    for i, m in enumerate(sorted(unique_meetings, key=lambda x: x.get('start', '')), 1):
        source_name = m.get('source', 'Unknown')
        title = m.get('title', 'N/A')
        date = m.get('start', 'N/A')
        print(f"  {i}. [{source_name}] {title} - {date}")
