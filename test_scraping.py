#!/usr/bin/env python3
"""
Test script to verify the event scraping functionality
"""
import sys
import os
sys.path.append('backend')

from main import scrape_site

def test_scraping():
    """Test the scraping functionality"""
    print("Testing event scraping...")
    
    # Test visitvaldosta.org
    print("\n=== Testing visitvaldosta.org ===")
    events1 = scrape_site("https://visitvaldosta.org/events/")
    print(f"Found {len(events1)} events from visitvaldosta.org")
    
    for i, event in enumerate(events1[:3]):  # Show first 3 events
        print(f"Event {i+1}:")
        print(f"  Title: {event['title']}")
        print(f"  Date: {event['start']}")
        print(f"  URL: {event['url']}")
        print(f"  Description: {event['description'][:100]}...")
        print()
    
    # Test valdostamainstreet.com
    print("\n=== Testing valdostamainstreet.com ===")
    events2 = scrape_site("https://www.valdostamainstreet.com/events-calendar")
    print(f"Found {len(events2)} events from valdostamainstreet.com")
    
    for i, event in enumerate(events2[:3]):  # Show first 3 events
        print(f"Event {i+1}:")
        print(f"  Title: {event['title']}")
        print(f"  Date: {event['start']}")
        print(f"  URL: {event['url']}")
        print(f"  Description: {event['description'][:100]}...")
        print()
    
    total_events = len(events1) + len(events2)
    print(f"\nTotal events found: {total_events}")
    
    if total_events > 0:
        print("✅ Scraping test PASSED - Events found!")
    else:
        print("❌ Scraping test FAILED - No events found!")

if __name__ == "__main__":
    test_scraping()
