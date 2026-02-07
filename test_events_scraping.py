"""Test Events scraping to see why count increased"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import source_manager, generic_scraper
from collections import defaultdict

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

print("="*80)
print("TESTING EVENTS SCRAPING (Should return 82 events)")
print("="*80)

if not client:
    print("ERROR: OpenAI client not available")
    sys.exit(1)

# Simulate what the backend does
sources = source_manager.get_sources_by_type('events')
print(f"\nFound {len(sources)} event sources")

all_items = []
for source in sources:
    print(f"\nScraping: {source['name']}")
    print(f"  URL: {source['url']}")
    print(f"  Type: {source['type']}")
    print(f"  Method: {source.get('scraping_method', 'auto')}")

    try:
        scraping_method = source.get('scraping_method', 'auto')
        if scraping_method in ['ai', 'ai_twostage']:
            items = generic_scraper.scrape_with_ai(
                source['url'],
                source['type'],
                client,
                scraping_method
            )
        else:
            items = generic_scraper.scrape_generic_auto(source['url'], source['type'])

        print(f"  ✅ Found {len(items)} items")
        all_items.extend(items)

    except Exception as e:
        print(f"  ❌ Error: {e}")

print(f"\n{'='*80}")
print(f"BEFORE DEDUPLICATION: {len(all_items)} total items")
print(f"{'='*80}")

# Group by source to see distribution
by_source = defaultdict(list)
for item in all_items:
    # Try to identify source from URL or title
    source_name = "Unknown"
    item_url = item.get('url', '')
    if 'visitvaldosta.org' in item_url:
        source_name = 'Visit Valdosta'
    elif 'valdostacity.com' in item_url:
        source_name = 'Valdosta City'
    elif 'valdostachamber.com' in item_url or 'business.valdostachamber' in item_url:
        source_name = 'Chamber of Commerce'
    elif 'valdosta.edu' in item_url:
        source_name = 'VSU Concert'
    elif 'turnercenter.org' in item_url:
        source_name = '⚠️ TURNER CENTER (Should NOT be here!)'

    by_source[source_name].append(item)

for source_name in sorted(by_source.keys()):
    items = by_source[source_name]
    print(f"  {source_name}: {len(items)} items")
    if 'TURNER' in source_name:
        print("    ⚠️ WARNING: Turner Center items found in Events!")
        for item in items[:3]:  # Show first 3
            print(f"      - {item.get('title', 'No title')}")

# Now deduplicate (simulating what backend does)
print(f"\n{'='*80}")
print("DEDUPLICATION...")
print(f"{'='*80}")

# Import deduplication function from main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from main import deduplicate_events

unique_items = deduplicate_events(all_items)
print(f"AFTER DEDUPLICATION: {len(unique_items)} unique items")

print(f"\n{'='*80}")
print(f"RESULT: {'✅ CORRECT (82)' if len(unique_items) == 82 else f'❌ INCORRECT (Expected 82, got {len(unique_items)})'}")
print(f"{'='*80}")
