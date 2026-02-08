#!/usr/bin/env python3
"""
Test to see if recurring pattern expansion is causing the 13 vs 8 meetings issue.
The difference is 5 extra meetings, which suggests incorrect expansion.
"""
import sys
sys.path.insert(0, 'backend')

from backend import generic_scraper
from openai import OpenAI
import os
import json

# Load API key
from dotenv import load_dotenv
load_dotenv('backend/.env')

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

url = "https://lowndescounty.com/calendar.aspx?CID=23&Keywords=&startDate=&enddate=&"

print("="*80)
print("TESTING LOWNDES COUNTY EXPANSION BUG")
print("="*80)
print("Looking for recurring pattern issues that could cause 13 meetings instead of 8")
print()

# Run once and inspect the results in detail
results = generic_scraper.scrape_with_ai(url, 'meetings', client, "ai_twostage")

print(f"\nTotal meetings found: {len(results)}")
print("\nDetailed inspection:")
print("="*80)

# Group by title to see if any are being duplicated
from collections import defaultdict
by_title = defaultdict(list)

for meeting in results:
    title = meeting.get('title', 'N/A')
    by_title[title].append(meeting)

print(f"\nUnique meeting titles: {len(by_title)}")
print("\nMeetings grouped by title:")

for title, meetings in sorted(by_title.items()):
    print(f"\n{title}")
    print(f"  Count: {len(meetings)} occurrence(s)")
    for m in meetings:
        date = m.get('start', 'N/A')
        recurring = m.get('recurring_pattern', '')
        print(f"    - Date: {date}")
        if recurring and recurring != 'None' and recurring != '':
            print(f"      Recurring: '{recurring}'")
        print(f"      Full data: {json.dumps(m, indent=6)}")

# Check for any recurring patterns
recurring_meetings = [m for m in results if m.get('recurring_pattern') and m.get('recurring_pattern') not in ['', 'None', 'unknown']]
print(f"\n{'='*80}")
print(f"Meetings with recurring patterns: {len(recurring_meetings)}")
if recurring_meetings:
    print("\nWARNING: These meetings have recurring patterns that might get expanded:")
    for m in recurring_meetings:
        print(f"  - {m.get('title')}: {m.get('recurring_pattern')}")
        print(f"    Date: {m.get('start')}")

# Check for 'unknown' patterns
unknown_meetings = [m for m in results if m.get('recurring_pattern') == 'unknown']
if unknown_meetings:
    print(f"\n{'='*80}")
    print(f"Meetings with 'unknown' recurring pattern: {len(unknown_meetings)}")
    print("NOTE: 'unknown' should NOT trigger expansion, but let's verify:")
    for m in unknown_meetings:
        print(f"  - {m.get('title')} on {m.get('start')}")
