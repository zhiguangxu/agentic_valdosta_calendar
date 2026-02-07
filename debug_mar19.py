"""Debug: Check what events are on Mar 19"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI
from backend import source_manager
from backend import generic_scraper
from backend.main import deduplicate_events

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

if not client:
    print("ERROR: OpenAI client not available")
    sys.exit(1)

# Get events sources
sources = source_manager.get_sources_by_type('events')
print(f"{'='*80}")
print(f"DEBUGGING MAR 19 DUPLICATES")
print(f"{'='*80}\n")

all_events = []
for source in sources:
    print(f"\nScraping: {source['name']}")
    print(f"  URL: {source['url']}")
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

        # Check for Mar 19 events in this source
        mar19_items = [e for e in items if e.get('start', '').startswith('2026-03-19')]
        if mar19_items:
            print(f"  ✅ Found {len(mar19_items)} Mar 19 events from this source:")
            for e in mar19_items:
                print(f"    - {e.get('title')}")
        else:
            print(f"  No Mar 19 events from this source")

        all_events.extend(items)
    except Exception as e:
        print(f"  ❌ Error: {e}")

print(f"\n{'='*80}")
print(f"BEFORE DEDUPLICATION")
print(f"{'='*80}")

mar19_before = [e for e in all_events if e.get('start', '').startswith('2026-03-19')]
print(f"\nTotal Mar 19 events BEFORE dedup: {len(mar19_before)}\n")
for idx, e in enumerate(mar19_before, 1):
    print(f"{idx}. {e.get('title')}")
    print(f"   Start: {e.get('start')}")
    print(f"   URL: {e.get('url', 'No URL')[:80]}")
    print(f"   Description: {e.get('description', 'No description')[:100]}")
    print()

print(f"{'='*80}")
print(f"AFTER DEDUPLICATION")
print(f"{'='*80}")

deduplicated = deduplicate_events(all_events)
mar19_after = [e for e in deduplicated if e.get('start', '').startswith('2026-03-19')]
print(f"\nTotal Mar 19 events AFTER dedup: {len(mar19_after)}\n")
for idx, e in enumerate(mar19_after, 1):
    print(f"{idx}. {e.get('title')}")
    print(f"   Start: {e.get('start')}")
    print(f"   URL: {e.get('url', 'No URL')[:80]}")
    print(f"   Description: {e.get('description', 'No description')[:100]}")
    print()

if len(mar19_after) > 1:
    print(f"{'='*80}")
    print(f"⚠️  DUPLICATE DETECTED!")
    print(f"{'='*80}")
    print(f"\nDeduplication failed to merge these {len(mar19_after)} events.")
    print(f"Analyzing why they weren't deduplicated...\n")

    for idx, e in enumerate(mar19_after, 1):
        title = e.get('title', '').lower().strip()
        normalized = title
        # Apply same normalization as deduplicate_events
        import re
        normalized = re.sub(r'^\d+(st|nd|rd|th)\s+annual\s+', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'^annual\s+', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'^20\d{2}\s+', '', normalized)
        for prefix in ['the ', 'a ', 'an ']:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())

        date = e.get('start', '').split('T')[0]
        dedup_key = f"{date}_{normalized[:50]}"

        print(f"Event {idx}:")
        print(f"  Original title: {e.get('title')}")
        print(f"  Normalized: {normalized}")
        print(f"  Dedup key: {dedup_key}")
        print()
