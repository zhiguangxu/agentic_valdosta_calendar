#!/usr/bin/env python3
"""
Test script to verify the Wanderlog scraping functionality
"""
import sys
import os
sys.path.append('backend')

from main import scrape_site

def test_wanderlog_scraping():
    """Test the Wanderlog scraping functionality"""
    print("Testing Wanderlog attraction scraping...")
    
    # Test wanderlog.com
    print("\n=== Testing wanderlog.com ===")
    attractions = scrape_site("https://wanderlog.com/list/geoCategory/1592203/top-things-to-do-and-attractions-in-valdosta")
    print(f"Found {len(attractions)} attractions from Wanderlog")
    
    for i, attraction in enumerate(attractions[:5]):  # Show first 5 attractions
        print(f"Attraction {i+1}:")
        print(f"  Title: {attraction['title']}")
        print(f"  URL: {attraction['url']}")
        print(f"  Categories: {attraction.get('categories', [])}")
        print(f"  Description: {attraction['description'][:100]}...")
        print()
    
    if len(attractions) > 0:
        print("✅ Wanderlog scraping test PASSED - Attractions found!")
    else:
        print("❌ Wanderlog scraping test FAILED - No attractions found!")

if __name__ == "__main__":
    test_wanderlog_scraping()
