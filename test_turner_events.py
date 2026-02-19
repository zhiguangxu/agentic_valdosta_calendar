#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar/backend')

from generic_scraper import scrape_events

# Test Turner Center events scraping
url = "https://turnercenter.org/events/"
print("Scraping Turner Center events...")
events = scrape_events(url, "events")

print(f"\nTotal Turner Center events scraped: {len(events)}")
print("\nTurner Center Events:")
for i, event in enumerate(events, 1):
    print(f"\n{i}. {event.get('title', 'NO TITLE')}")
    print(f"   Start: {event.get('start', 'NO START')}")
    print(f"   Description: {event.get('description', 'NO DESC')[:100]}...")
