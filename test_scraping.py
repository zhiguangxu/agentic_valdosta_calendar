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
    
    # Test wanderlog.com
    print("\n=== Testing wanderlog.com ===")
    attractions1 = scrape_site("https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta")
    print(f"Found {len(attractions1)} attractions from Wanderlog")
    
    for i, attraction in enumerate(attractions1[:2]):  # Show first 2 attractions
        print(f"Attraction {i+1}:")
        print(f"  Title: {attraction['title']}")
        print(f"  URL: {attraction['url']}")
        print(f"  Categories: {attraction.get('categories', [])}")
        print(f"  Description: {attraction['description'][:100]}...")
        print()
    
    # Test exploregeorgia.org
    print("\n=== Testing exploregeorgia.org ===")
    attractions2 = scrape_site("https://exploregeorgia.org/article/guide-to-valdosta")
    print(f"Found {len(attractions2)} attractions from Explore Georgia")
    
    for i, attraction in enumerate(attractions2[:2]):  # Show first 2 attractions
        print(f"Attraction {i+1}:")
        print(f"  Title: {attraction['title']}")
        print(f"  URL: {attraction['url']}")
        print(f"  Categories: {attraction.get('categories', [])}")
        print(f"  Description: {attraction['description'][:100]}...")
        print()
    
    # Test tripadvisor.com
    print("\n=== Testing tripadvisor.com ===")
    attractions3 = scrape_site("https://www.tripadvisor.com/Attractions-g35335-Activities-Valdosta_Georgia.html")
    print(f"Found {len(attractions3)} attractions from TripAdvisor")
    
    for i, attraction in enumerate(attractions3[:2]):  # Show first 2 attractions
        print(f"Attraction {i+1}:")
        print(f"  Title: {attraction['title']}")
        print(f"  URL: {attraction['url']}")
        print(f"  Categories: {attraction.get('categories', [])}")
        print(f"  Description: {attraction['description'][:100]}...")
        print()
    
    total_events = len(events1) + len(events2)
    total_attractions = len(attractions1) + len(attractions2) + len(attractions3)
    print(f"\nTotal events found: {total_events}")
    print(f"Total attractions found: {total_attractions}")
    
    if total_events > 0 or total_attractions > 0:
        print("✅ Scraping test PASSED - Content found!")
    else:
        print("❌ Scraping test FAILED - No content found!")

if __name__ == "__main__":
    test_scraping()
