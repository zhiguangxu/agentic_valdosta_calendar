#!/usr/bin/env python3
"""
Test script to investigate inconsistent scraping results from Lowndes County meetings.
Runs multiple scraping attempts and compares results.
"""
import sys
sys.path.insert(0, 'backend')

from backend import generic_scraper
from openai import OpenAI
import os
import json
from collections import Counter

# Load API key
from dotenv import load_dotenv
load_dotenv('backend/.env')

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found")
    sys.exit(1)

client = OpenAI(api_key=openai_api_key)

# Test URL
url = "https://lowndescounty.com/calendar.aspx?CID=23&Keywords=&startDate=&enddate=&"
source_type = "meetings"

print("="*80)
print("LOWNDES COUNTY MEETINGS CONSISTENCY TEST")
print("="*80)
print(f"URL: {url}")
print(f"Type: {source_type}")
print(f"Running 3 scraping attempts to check for consistency...\n")

# Run multiple scraping attempts
results_list = []
for attempt in range(1, 4):
    print(f"\n{'='*80}")
    print(f"ATTEMPT {attempt}")
    print(f"{'='*80}")

    results = generic_scraper.scrape_with_ai(url, source_type, client, "ai_twostage")
    results_list.append(results)

    print(f"\n[ATTEMPT {attempt}] Total meetings found: {len(results)}")
    print(f"\n[ATTEMPT {attempt}] Meeting titles:")
    for i, meeting in enumerate(sorted(results, key=lambda x: x.get('start', '')), 1):
        title = meeting.get('title', 'N/A')
        start = meeting.get('start', 'N/A')
        recurring = meeting.get('recurring_pattern', '')
        print(f"  {i}. {title}")
        print(f"     Date: {start}")
        if recurring:
            print(f"     Recurring: {recurring}")

# Analysis
print(f"\n{'='*80}")
print("ANALYSIS")
print(f"{'='*80}")

counts = [len(r) for r in results_list]
print(f"Counts per attempt: {counts}")
print(f"Min: {min(counts)}, Max: {max(counts)}, Avg: {sum(counts)/len(counts):.1f}")

if len(set(counts)) > 1:
    print("\n⚠️  INCONSISTENCY DETECTED: Different counts across attempts!")
else:
    print("\n✅ CONSISTENT: Same count across all attempts")

# Check which titles appear in each attempt
all_titles = []
for results in results_list:
    all_titles.extend([f"{m.get('title', '')}|{m.get('start', '')}" for m in results])

title_counts = Counter(all_titles)

print(f"\n\nTitle frequency across all attempts:")
for title_date, count in sorted(title_counts.items(), key=lambda x: (-x[1], x[0])):
    title, date = title_date.split('|', 1)
    if count < 3:
        print(f"  ⚠️  Appears {count}/3 times: {title} on {date}")
    else:
        print(f"  ✅ Appears {count}/3 times: {title} on {date}")

# Check for unique titles
unique_to_attempts = {}
for i, results in enumerate(results_list, 1):
    titles_set = set([f"{m.get('title', '')}|{m.get('start', '')}" for m in results])
    for j, other_results in enumerate(results_list, 1):
        if i != j:
            other_titles = set([f"{m.get('title', '')}|{m.get('start', '')}" for m in other_results])
            unique = titles_set - other_titles
            if unique:
                if i not in unique_to_attempts:
                    unique_to_attempts[i] = []
                unique_to_attempts[i].extend(unique)

if unique_to_attempts:
    print(f"\n\nMeetings that appear in some attempts but not others:")
    for attempt_num, unique_meetings in unique_to_attempts.items():
        if unique_meetings:
            print(f"\n  Unique to Attempt {attempt_num}:")
            for title_date in set(unique_meetings):
                title, date = title_date.split('|', 1)
                print(f"    - {title} on {date}")
