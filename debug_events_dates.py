"""Debug: Check what events are being scraped and their dates"""
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

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

if not client:
    print("ERROR: OpenAI client not available")
    sys.exit(1)

# Get events sources
sources = source_manager.get_sources_by_type('events')
print(f"{'='*80}")
print(f"CHECKING EVENTS SOURCES FOR DATE ISSUES")
print(f"{'='*80}")

# Import after we've added backend to path
from backend.main import _scrape_calendar_category

# Scrape events
events = _scrape_calendar_category('events', sources)

print(f"\n{'='*80}")
print(f"LOOKING FOR BROADWAY BOYS AND DOO WOP PROJECT")
print(f"{'='*80}\n")

broadway_events = [e for e in events if 'broadway boys' in e.get('title', '').lower()]
doowop_events = [e for e in events if 'doo wop' in e.get('title', '').lower()]

print(f"Broadway Boys events found: {len(broadway_events)}")
for e in broadway_events:
    date = e.get('start', '').split('T')[0]
    print(f"  - {e.get('title')} on {date}")
    print(f"    URL: {e.get('url', 'No URL')}")
    print(f"    Description: {e.get('description', 'No description')[:100]}")

print(f"\nDoo Wop Project events found: {len(doowop_events)}")
for e in doowop_events:
    date = e.get('start', '').split('T')[0]
    print(f"  - {e.get('title')} on {date}")
    print(f"    URL: {e.get('url', 'No URL')}")
    print(f"    Description: {e.get('description', 'No description')[:100]}")

print(f"\n{'='*80}")
print(f"CHECKING FOR EVENTS ON FEB 26 AND MAR 19")
print(f"{'='*80}\n")

feb26_events = [e for e in events if e.get('start', '').startswith('2026-02-26')]
mar19_events = [e for e in events if e.get('start', '').startswith('2026-03-19')]

print(f"Events on Feb 26 ({len(feb26_events)}):")
for e in feb26_events:
    print(f"  - {e.get('title')}")
    print(f"    URL: {e.get('url', 'No URL')[:80]}")

print(f"\nEvents on Mar 19 ({len(mar19_events)}):")
for e in mar19_events:
    print(f"  - {e.get('title')}")
    print(f"    URL: {e.get('url', 'No URL')[:80]}")
