"""
Generic Scraper - Intelligently scrapes events/attractions from any website
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from urllib.parse import urljoin
from typing import List, Dict, Optional
from openai import OpenAI
import os
import json


def scrape_with_ai(url: str, source_type: str, openai_client: Optional[OpenAI],
                   scraping_method: str = "ai") -> List[Dict]:
    """Use AI to intelligently scrape any website with post-processing for consistency"""
    if not openai_client:
        print(f"OpenAI client not available for AI scraping {url}")
        return []

    # Two-stage scraping for problematic listing pages
    # Support all calendar-based types: events, classes, meetings
    if scraping_method == "ai_twostage" and source_type in ["events", "classes", "meetings"]:
        return _scrape_twostage(url, openai_client, source_type)

    try:
        from dateutil.relativedelta import relativedelta

        # Use moderate headers - enough to bypass most blocks, but not so many as to trigger bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

        all_results = []

        # For calendar-based event sites, try to fetch multiple months
        # (Attractions don't need this - they're not date-specific)
        urls_to_process = [url]
        if source_type == 'events':
            # Check if this might be a calendar site by fetching and checking for tables
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # If we find a calendar table, fetch multiple months
                if soup.find("table"):
                    current_date = datetime.now()
                    for i in range(1, 7):  # Get next 6 months
                        month_date = current_date + relativedelta(months=i)
                        month_str = month_date.strftime("%Y-%m")
                        if '?' in url:
                            month_url = f"{url.split('?')[0]}?month={month_str}"
                        else:
                            month_url = f"{url}?month={month_str}"
                        urls_to_process.append(month_url)
                    print(f"  Detected calendar site, will process {len(urls_to_process)} months")
            except:
                pass  # If detection fails, just process the single URL
        else:
            print(f"  Scraping attractions from single page")

        # Process each URL (current month + future months if calendar site)
        for process_url in urls_to_process:
            try:
                resp = requests.get(process_url, headers=headers, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove script, style, nav, footer, and header elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                # Extract meaningful HTML structure (not just text)
                # Keep semantic structure: links, dates, headings, containers
                content_html = ""
                char_limit = 100000 if source_type == 'attractions' else 50000  # More content for attractions

                # Strategy 1: Find main content containers (works for most sites)
                main_content = soup.find(["main", "article"]) or soup.find("div", class_=re.compile(r"main|content|body", re.I))
                use_simplified = False

                if main_content:
                    # If main container is too small, it's probably empty (JS-rendered content)
                    if len(str(main_content)) < 1000:
                        print(f"  HTML extraction: Main container too small ({len(str(main_content))} chars), trying other strategies")
                        main_content = None  # Force fallback to other strategies
                    elif source_type == 'attractions':
                        # For attractions, always use simplified extraction (not raw HTML)
                        print(f"  HTML extraction: Found main container ({len(str(main_content))} chars), will simplify for attractions")
                        # Replace soup with main_content for searching
                        soup = BeautifulSoup(str(main_content), "html.parser")
                        use_simplified = True
                        main_content = None  # Force to use simplified extraction below
                    else:
                        content_html = str(main_content)[:char_limit]
                        print(f"  HTML extraction: Using main/article container ({len(content_html)} chars)")

                if not main_content or use_simplified:
                    # Strategy 2: Get all potentially relevant containers
                    # For attractions, be more aggressive in finding content
                    if source_type == 'attractions':
                        containers = soup.find_all(["article", "div", "li", "section", "h2", "h3"],
                                                   class_=re.compile(r"place|card|item|entry|post|listing|location|destination|attraction|thing", re.I),
                                                   limit=200)  # More items for attractions
                    else:
                        containers = soup.find_all(["article", "div", "li", "section"],
                                                   class_=re.compile(r"event|attraction|place|card|item|entry|post|listing", re.I),
                                                   limit=100)

                    if containers:
                        # For attractions, simplify HTML to make it easier for AI to parse
                        if source_type == 'attractions':
                            simplified_items = []

                            # Strategy A: Extract from containers
                            for idx, container in enumerate(containers[:200], 1):
                                title = container.find(['h2', 'h3', 'h4', 'a'])
                                title_text = title.get_text(strip=True) if title else ""

                                desc = container.find('p')
                                desc_text = desc.get_text(strip=True)[:200] if desc else ""

                                link = container.find('a', href=True)
                                link_url = link['href'] if link else ""

                                if title_text and len(title_text) > 3:
                                    simplified_items.append(f"ITEM {idx}:\nTitle: {title_text}\nDescription: {desc_text}\nURL: {link_url}\n")

                            # Strategy B: Also find all h2/h3/h4 headers directly (like article-style fallback)
                            # This catches items that aren't in proper containers
                            headers = soup.find_all(['h2', 'h3', 'h4'], limit=200)
                            seen_titles = {item.split('\n')[1].replace('Title: ', '') for item in simplified_items}

                            for header in headers:
                                title_text = header.get_text(strip=True)

                                # Skip if already found or too short (match generic_auto threshold)
                                if len(title_text) < 3 or title_text in seen_titles:
                                    continue

                                # Skip generic section headers
                                if title_text.lower() in ['things to do', 'attractions', 'events', 'overview', 'about', 'places', 'restaurants']:
                                    continue

                                seen_titles.add(title_text)

                                # Find description in following paragraph
                                desc_text = ""
                                next_elem = header.find_next_sibling(['p', 'div'])
                                if next_elem:
                                    desc_text = next_elem.get_text(strip=True)[:200]

                                # Find link
                                link = header.find('a') or (next_elem.find('a') if next_elem else None)
                                link_url = link['href'] if link and link.get('href') else ""

                                # Skip if it's a link to another article (not an actual place)
                                if link_url and '/article/' in link_url:
                                    continue

                                simplified_items.append(f"ITEM {len(simplified_items)+1}:\nTitle: {title_text}\nDescription: {desc_text}\nURL: {link_url}\n")

                            content_html = "\n".join(simplified_items)[:char_limit]
                            print(f"  HTML extraction: Found {len(simplified_items)} items from containers + headers ({len(content_html)} chars)")
                        else:
                            content_html = "\n".join([str(c) for c in containers])[:char_limit]
                            print(f"  HTML extraction: Using {len(containers)} containers ({len(content_html)} chars)")
                    else:
                        # Strategy 3: If there's a table (calendar site), get it with context
                        table = soup.find("table")
                        if table:
                            # Get the parent container that includes the table
                            parent = table.find_parent(["div", "section", "main"])
                            content_html = str(parent)[:char_limit] if parent else str(table)[:char_limit]
                            print(f"  HTML extraction: Using table with context ({len(content_html)} chars)")
                        else:
                            # Fallback: Get body content
                            content_html = str(soup.body)[:char_limit] if soup.body else str(soup)[:char_limit]
                            print(f"  HTML extraction: Using body fallback ({len(content_html)} chars)")

                # Use AI to extract events/classes/meetings/attractions
                current_year = datetime.now().year
                current_month = datetime.now().month

                # Create source-type specific prompts using helper functions
                if source_type == 'events':
                    prompt = _generate_events_prompt(content_html, current_year)
                elif source_type == 'classes':
                    prompt = _generate_classes_prompt(content_html, current_year)
                elif source_type == 'meetings':
                    prompt = _generate_meetings_prompt(content_html, current_year)
                else:  # attractions
                    prompt = f"""
Extract ALL attractions from the structured list below. Each ITEM represents one place/attraction.

RULES:
1. Extract EVERY item in the list
2. Skip ONLY if the title is a generic category (1-2 words like "Food", "Museums") - but include specific places even if short
3. Use the Title, Description, and URL exactly as provided
4. Add date "{datetime.now().strftime("%Y-%m-%d")}" and time "10:00" to all items

INPUT FORMAT - Each item looks like this:
ITEM X:
Title: [Place Name]
Description: [Description text]
URL: [URL path]

YOUR TASK:
Convert each ITEM into JSON format. If you see 50 items, return 50 JSON objects.

Return ONLY a JSON array (no markdown, no extra text):
[
  {{"title": "Title from item", "date": "{datetime.now().strftime("%Y-%m-%d")}", "time": "10:00", "description": "Description from item", "url": "URL from item"}},
  ...
]

ITEMS:
{content_html}
"""

                # Use more powerful model for attractions (complex HTML structures)
                model = "gpt-4o" if source_type == 'attractions' else "gpt-4o-mini"

                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1  # Lower temperature for more consistency
                )

                if source_type == 'attractions':
                    print(f"  Using {model} model for better extraction")

                raw_output = response.choices[0].message.content.strip()

                # Clean JSON markers
                if raw_output.startswith("```json"):
                    raw_output = raw_output[7:]
                if raw_output.startswith("```"):
                    raw_output = raw_output[3:]
                if raw_output.endswith("```"):
                    raw_output = raw_output[:-3]
                raw_output = raw_output.strip()

                # Parse JSON
                try:
                    items = json.loads(raw_output)
                    print(f"  AI extracted {len(items)} items from {process_url}")
                    if items:
                        print(f"  Sample item: {items[0]}")
                except json.JSONDecodeError as e:
                    print(f"  ERROR: Failed to parse AI response as JSON: {e}")
                    print(f"  Raw output was: {raw_output[:500]}...")
                    items = []

                # Process each item with post-processing
                for item in items:
                    date_str = item.get('date', datetime.now().strftime("%Y-%m-%d"))
                    time_str = item.get('time', '19:00' if source_type == 'events' else '10:00')
                    title = item.get('title', 'Untitled')
                    item_url = item.get('url', url)

                    # Resolve relative URLs
                    if item_url.startswith("/"):
                        item_url = urljoin(url, item_url)

                    # Parse and validate date
                    if source_type == 'events':
                        # Smart year handling for events
                        try:
                            parsed_date = dateparser.parse(date_str)
                            if parsed_date:
                                current_date = datetime.now()

                                # Smart year bumping based on month difference
                                # If the event month is more than 2 months in the past, assume next year
                                # This handles: Nov viewing Jan/Feb/Mar → next year
                                # But keeps: Nov viewing Oct/Nov → current year (recent past events)
                                months_diff = (current_date.year - parsed_date.year) * 12 + (current_date.month - parsed_date.month)

                                if months_diff > 2:
                                    # Event is from 3+ months ago, assume it's for next year
                                    parsed_date = parsed_date.replace(year=parsed_date.year + 1)
                                elif months_diff < 0:
                                    # Event is in a future month of current year, keep as-is
                                    pass
                                elif months_diff <= 2 and parsed_date.date() < current_date.date():
                                    # Event is in current or recent past month and date has passed
                                    # Keep as current year (will be filtered as past event)
                                    pass

                                date_str = parsed_date.strftime("%Y-%m-%d")
                            else:
                                # If parsing fails, use today's date as fallback
                                date_str = datetime.now().strftime("%Y-%m-%d")
                        except:
                            date_str = datetime.now().strftime("%Y-%m-%d")
                    else:
                        # For attractions, always use today's date (they're not time-specific)
                        date_str = datetime.now().strftime("%Y-%m-%d")

                    # Validate and fix time format
                    if not re.match(r'^\d{2}:\d{2}$', time_str):
                        time_str = '19:00' if source_type == 'events' else '10:00'

                    result_item = {
                        "title": title,
                        "url": item_url,
                        "description": item.get('description', ''),
                        "start": f"{date_str}T{time_str}:00",
                        "allDay": False
                    }
                    print(f"    Adding: {title} on {date_str}")
                    all_results.append(result_item)

            except Exception as e:
                print(f"  Error processing {process_url}: {e}")
                continue

        # Apply post-processing for consistency (like scrape_generic_auto does)
        results = _post_process_ai_results(all_results, source_type, url)

        print(f"AI extracted {len(results)} items from {url} (processed {len(urls_to_process)} pages)")
        return results

    except Exception as e:
        print(f"Error in AI scraping for {url}: {e}")
        return []


def _generate_events_prompt(content_html: str, current_year: int) -> str:
    """Generate AI prompt specifically for events extraction"""
    return f"""
You are an expert web scraper. Extract EVENTS information from the following HTML content.

TODAY'S DATE: {datetime.now().strftime("%Y-%m-%d")}
CURRENT YEAR: {current_year}

IMPORTANT INSTRUCTIONS:
1. Extract ALL events you can find, not just a few examples - INCLUDE ALL calendar entries
2. For dates: Use YYYY-MM-DD format. The current year is {current_year}. For dates without a year, assume {current_year}. If a date (like "November 13") has already passed in {current_year}, assume it's for the NEXT year ({current_year + 1}).
3. For times: Use HH:MM 24-hour format. Look for times in the content. If no time found, use "19:00"
4. For URLs: Extract href attributes from <a> tags. Return relative URLs as-is (e.g., "/event/123")
5. For titles: Extract the event name exactly as shown - keep all calendar entries
6. EXCLUDE ONLY: Navigation items and UI elements like "Log In", "Sign Up", "Read More", "Menu", "Search", "Home", "About", "Contact"
7. For descriptions: Extract from paragraph text, keep it under 200 characters

Return ONLY a valid JSON array with no markdown formatting or additional text. Format:
[
  {{"title": "Event Name", "date": "{current_year}-01-15", "time": "19:00", "description": "Brief description", "url": "/event/123"}},
  {{"title": "Another Event", "date": "{current_year}-02-20", "time": "14:00", "description": "Another description", "url": "/event/456"}}
]

If you cannot find any events, return an empty array: []

HTML content:
{content_html}
"""


def _generate_classes_prompt(content_html: str, current_year: int) -> str:
    """Generate AI prompt specifically for classes extraction"""
    return f"""
You are an expert web scraper. Extract CLASS/WORKSHOP information from the following HTML content.

TODAY'S DATE: {datetime.now().strftime("%Y-%m-%d")}
CURRENT YEAR: {current_year}

CLASSES-SPECIFIC INSTRUCTIONS:
1. Extract ALL classes/workshops you can find
2. For titles: Keep full class names including instructors (e.g., "Drawing Class with Jane Smith")
3. For instructors: Try to identify the instructor name from the content
4. For dates: Use YYYY-MM-DD format. Classes may be ongoing or recurring - extract start dates
5. For times: Use HH:MM 24-hour format. Default to "10:00" for morning classes, "14:00" for afternoon
6. For skill level: Note if the class mentions "beginner", "intermediate", "advanced"
7. For descriptions: Include instructor, skill level, what students will learn, materials needed (200-300 chars)
8. IMPORTANT: Keep ordinals like "2nd Week", "Week 3" - these are meaningful for classes
9. Look for recurring schedules: "Every Monday", "Wednesdays 2-4pm", "Monthly workshop"

Return ONLY a valid JSON array with no markdown formatting. Format:
[
  {{"title": "Class Name with Instructor", "date": "{current_year}-02-15", "time": "14:00", "description": "Detailed class description with instructor, skill level, what you'll learn", "url": "/class/123", "instructor": "Instructor Name", "skill_level": "beginner"}}
]

If you cannot find any classes, return an empty array: []

HTML content:
{content_html}
"""


def _generate_meetings_prompt(content_html: str, current_year: int) -> str:
    """Generate AI prompt specifically for meetings extraction"""
    return f"""
You are an expert web scraper. Extract MEETING information from the following HTML content.

TODAY'S DATE: {datetime.now().strftime("%Y-%m-%d")}
CURRENT YEAR: {current_year}

MEETINGS-SPECIFIC INSTRUCTIONS:
1. Extract ALL meetings you can find
2. For titles: Use exact meeting names - be precise (e.g., "City Council Meeting", "Board of Directors Meeting")
3. For locations: Extract meeting location/venue (e.g., "City Hall Room 203")
4. For dates: Use YYYY-MM-DD format. Current year is {current_year}
5. For times: Use HH:MM 24-hour format. Meetings often have exact start times - extract them precisely
6. For descriptions: Include agenda items, attendees, purpose of meeting (200 chars)
7. Look for recurring patterns: "Monthly meeting", "Every 3rd Tuesday", "Quarterly review"
8. IMPORTANT: Keep year prefixes if present (e.g., "2026 Annual Meeting")

Return ONLY a valid JSON array with no markdown formatting. Format:
[
  {{"title": "Meeting Name", "date": "{current_year}-02-15", "time": "18:00", "description": "Meeting purpose and agenda", "url": "/meeting/123", "location": "Meeting Location", "recurring_pattern": "Monthly on 3rd Tuesday"}}
]

If you cannot find any meetings, return an empty array: []

HTML content:
{content_html}
"""


def _truncate_description(desc: str, max_length: int = 150) -> str:
    """
    Truncate description to max_length, preferring to end at sentence boundary.
    """
    if not desc or len(desc) <= max_length:
        return desc

    # Try to truncate at sentence boundary (., !, ?)
    truncated = desc[:max_length]
    last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))

    if last_period > max_length * 0.6:  # If sentence boundary is > 60% through, use it
        return desc[:last_period + 1].strip()
    else:
        # Otherwise truncate at last space and add ellipsis
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space].strip() + '...'
        return truncated + '...'


def _generate_stage2_events_prompt(event_title: str, event_content: str, listing_date: str, today: datetime, six_months_later: datetime) -> str:
    """Generate Stage 2 AI prompt specifically for events"""
    date_hint = f"\nIMPORTANT: The listing page showed this event on {listing_date}. This is likely the correct date." if listing_date else ""

    return f"""
Extract ACCURATE date and schedule information from this event details page.

Item Title: {event_title}{date_hint}
Today's Date: {today.strftime("%Y-%m-%d")} ({today.strftime("%A, %B %d, %Y")})
Extract dates through: {six_months_later.strftime("%Y-%m-%d")} (next 6 months)

CRITICAL: If this page lists MULTIPLE events or dates, focus on finding the date for "{event_title}" specifically.
- If the page shows other events with different dates, ignore those dates
- Look for the date that matches the event title "{event_title}"
- Only extract dates that clearly belong to this specific event

INSTRUCTIONS:

1. RECURRING SCHEDULE DETECTION:
   - Look for recurring patterns like "First Friday", "Every Monday", "Monthly"
   - If found, generate ALL dates for the next 6 months
   - Return ALL generated dates in the "dates" array

2. SPECIFIC DATE EXTRACTION (FOR ONE-TIME EVENTS):
   - Look for specific dates like "Saturday, February 7, 2026"
   - CRITICAL: Return only ONE date unless this is a multi-day event
   - Do NOT extract dates for other events on the same page

3. TIME EXTRACTION:
   - Extract time like "7:00 PM" → "19:00" (24-hour format)
   - Default to "19:00" if no time found

4. DESCRIPTION EXTRACTION:
   - Extract a comprehensive description (200-300 characters)
   - Include: what it is, what attendees will experience

Return ONLY valid JSON:
{{
  "status": "active|cancelled|postponed|full|unknown",
  "dates": ["2026-02-14"],
  "recurring_pattern": "Optional: describe pattern",
  "time": "19:00",
  "description": "Detailed description",
  "corrected_title": "Only if page has BETTER title"
}}

HTML content:
{event_content}
"""


def _generate_stage2_classes_prompt(class_title: str, class_content: str, listing_date: str, today: datetime, six_months_later: datetime) -> str:
    """Generate Stage 2 AI prompt specifically for classes"""
    date_hint = f"\nIMPORTANT: The listing page showed this class starting on {listing_date}." if listing_date else ""

    return f"""
Extract ACCURATE schedule and class information from this class/workshop details page.

Class Title: {class_title}{date_hint}
Today's Date: {today.strftime("%Y-%m-%d")}
Extract dates through: {six_months_later.strftime("%Y-%m-%d")} (next 6 months)

CLASSES-SPECIFIC INSTRUCTIONS:

1. RECURRING SCHEDULE (VERY IMPORTANT FOR CLASSES):
   - Classes often meet weekly or multiple times
   - Look for patterns like: "Every Wednesday", "Tuesdays and Thursdays", "Weekly on Monday"
   - GENERATE ALL CLASS DATES for the next 6 months if recurring
   - Example: "Every Monday" → ["2026-02-10", "2026-02-17", "2026-02-24", ...]

2. CLASS SERIES / MULTI-WEEK:
   - Look for "6-week class", "8-session workshop"
   - Generate all session dates if weekly schedule is mentioned

3. TIME EXTRACTION:
   - Extract exact class time (e.g., "2:00 PM - 4:00 PM" → "14:00")
   - Default to "10:00" for morning, "14:00" for afternoon

4. DETAILED DESCRIPTION FOR CLASSES:
   - MUST include: instructor name, skill level, what students will learn
   - Include: materials needed, age group if specified
   - Example: "Learn watercolor techniques with Jane Smith. Beginner-friendly. Materials provided."

5. INSTRUCTOR:
   - Extract instructor name if mentioned

Return ONLY valid JSON:
{{
  "status": "active|cancelled|full|unknown",
  "dates": ["2026-02-10", "2026-02-17", ...],
  "recurring_pattern": "Every Monday 2-4pm",
  "time": "14:00",
  "description": "Class description with instructor, skill level, what you'll learn",
  "instructor": "Instructor Name",
  "corrected_title": "Only if page has BETTER title"
}}

HTML content:
{class_content}
"""


def _generate_stage2_meetings_prompt(meeting_title: str, meeting_content: str, listing_date: str, today: datetime, six_months_later: datetime) -> str:
    """Generate Stage 2 AI prompt specifically for meetings"""
    date_hint = f"\nIMPORTANT: The listing page showed this meeting on {listing_date}." if listing_date else ""

    return f"""
Extract ACCURATE date and meeting information from this meeting details page.

Meeting Title: {meeting_title}{date_hint}
Today's Date: {today.strftime("%Y-%m-%d")}
Extract dates through: {six_months_later.strftime("%Y-%m-%d")} (next 6 months)

MEETINGS-SPECIFIC INSTRUCTIONS:

1. RECURRING MEETINGS:
   - Look for patterns like "Monthly meeting", "Every 3rd Tuesday"
   - Generate ALL meeting dates for the next 6 months

2. EXACT DATE AND TIME:
   - Meetings usually have precise dates and times
   - Extract exact start time

3. LOCATION:
   - Extract meeting location/venue

4. AGENDA/PURPOSE:
   - Extract meeting agenda or purpose
   - Include who should attend

Return ONLY valid JSON:
{{
  "status": "active|cancelled|unknown",
  "dates": ["2026-02-18"],
  "recurring_pattern": "Monthly on 3rd Tuesday",
  "time": "18:00",
  "description": "Meeting agenda and purpose",
  "location": "Meeting Location",
  "corrected_title": "Only if page has BETTER title"
}}

HTML content:
{meeting_content}
"""


def _scrape_twostage(url: str, openai_client: OpenAI, source_type: str = "events") -> List[Dict]:
    """
    Two-stage scraping for event listing pages with unreliable dates.
    Stage 1: Extract event titles and external URLs from listing page
    Stage 2: Scrape each external URL for accurate date information
    """
    import time

    print(f"[Two-Stage] Starting two-stage scraping for {url}")

    # Stage 1: Extract event titles and URLs from listing page
    # Use different strategies based on site structure
    # BeautifulSoup structural parsing only for visitvaldosta.org (known structure)
    # AI extraction for all other sites (flexible, works with any structure)
    use_structural_parsing = "visitvaldosta.org" in url

    if use_structural_parsing:
        print(f"[Two-Stage] Stage 1: Extracting events from listing page (using BeautifulSoup)")
    else:
        print(f"[Two-Stage] Stage 1: Extracting events from listing page (using AI)")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        event_urls = []
        current_year = datetime.now().year

        # For calendar-based sites (e.g., valdostacity.com, chamber), fetch multiple months
        urls_to_process = [url]
        if not use_structural_parsing and soup.find("table"):
            from dateutil.relativedelta import relativedelta
            current_date = datetime.now()
            for i in range(1, 7):  # Get next 6 months
                month_date = current_date + relativedelta(months=i)
                month_str = month_date.strftime("%Y-%m")
                if '?' in url:
                    month_url = f"{url.split('?')[0]}?month={month_str}"
                else:
                    month_url = f"{url}?month={month_str}"
                urls_to_process.append(month_url)
            print(f"[Two-Stage] Detected calendar site, will process {len(urls_to_process)} months")

        # Process each URL (current month + future months if calendar)
        for process_url in urls_to_process:
            if process_url != url:
                resp = requests.get(process_url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

            if not use_structural_parsing:
                # AI-based extraction for sites with unknown structure
                # Remove unnecessary elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                # Get main content
                main_content = soup.find(["main", "article"]) or soup.find("div", class_=re.compile(r"main|content", re.I))
                # If main_content is too small (< 5000 chars), it's probably just navigation
                # Use full body instead to capture all event content
                if main_content and len(str(main_content)) < 5000:
                    print(f"  HTML extraction: Main container too small ({len(str(main_content))} chars), using full body")
                    # For sites with content deep in the page, use more content (up to 60000 chars)
                    html_content = str(soup.body)[:60000] if soup.body else str(soup)[:60000]
                elif main_content:
                    html_content = str(main_content)[:30000]
                else:
                    html_content = str(soup.body)[:60000] if soup.body else str(soup)[:60000]

                # Generate category-specific Stage 1 prompt
                if source_type == 'classes':
                    stage1_prompt = f"""
Extract class/workshop information from this page. For each class, extract:
1. The class title (include instructor if visible)
2. The URL where full class details can be found
3. The start date (YYYY-MM-DD format)
4. The time if available (HH:MM 24-hour format)
5. Recurring pattern (e.g., "Every Monday", "Weekly on Wednesday")

CLASSES-SPECIFIC:
- Look for class schedules, workshop listings
- Include instructor names in title if visible
- For recurring classes, note the schedule pattern
- Parse times: "2:00pm" → "14:00", default to "10:00" if not found
- Extract ALL upcoming classes

Return JSON: [{{"title": "...", "url": "...", "date": "...", "time": "...", "recurring_pattern": "..."}}]

HTML:
{html_content}
"""
                elif source_type == 'meetings':
                    stage1_prompt = f"""
Extract meeting information from this page. For each meeting, extract:
1. The meeting title (exact name)
2. The URL where full meeting details can be found
3. The date (YYYY-MM-DD format)
4. The time (HH:MM 24-hour format)
5. Recurring pattern (e.g., "Monthly on 3rd Tuesday")

MEETINGS-SPECIFIC:
- Look for meeting schedules, board meetings, council meetings
- Extract exact meeting times
- Note location if visible in listing
- For recurring meetings, note the pattern
- Extract ALL upcoming meetings

Return JSON: [{{"title": "...", "url": "...", "date": "...", "time": "...", "recurring_pattern": "..."}}]

HTML:
{html_content}
"""
                else:  # events (default)
                    stage1_prompt = f"""
Extract event information from this calendar page. For each event, extract:
1. The event title
2. The URL where full event details can be found (if available, otherwise leave empty)
3. The date (YYYY-MM-DD format)
4. The time if available (HH:MM 24-hour format)
5. Recurring pattern (if this is a recurring event, describe the pattern like "first friday of each month")

INSTRUCTIONS:
- Look for structured events (in tables, divs, or plain text lists)
- For plain-text calendars, look for patterns like:
  * "Day, Month Date" followed by event titles
  * "Event Title | Time | Venue"
  * Event listings under month headings
- DETECT RECURRING PATTERNS:
  * Look for phrases like "first friday", "every monday", "monthly", "weekly"
  * If found, include the pattern in recurring_pattern field
- If events don't have individual URLs, set url to empty string ""
- For calendar tables, look for links within cells
- Parse times: "7:00pm" → "19:00", "10:00am" → "10:00"
- Use current or upcoming year (2026) for dates
- Extract ALL future events from ALL months (February, March, April, May, etc.)
- Only skip events that are clearly in the past (before February 7, 2026)
- If multiple events occur on the same day, extract ALL of them

Return JSON array: [{{"title": "...", "url": "...", "date": "...", "time": "...", "recurring_pattern": "..."}}]

If no events found, return: []

HTML:
{html_content}
"""

                ai_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": stage1_prompt + "\n\nHTML:\n" + html_content}],
                    temperature=0.1
                )

                ai_raw = ai_response.choices[0].message.content.strip()
                if ai_raw.startswith("```json"):
                    ai_raw = ai_raw[7:]
                if ai_raw.startswith("```"):
                    ai_raw = ai_raw[3:]
                if ai_raw.endswith("```"):
                    ai_raw = ai_raw[:-3]
                ai_raw = ai_raw.strip()

                try:
                    extracted_events = json.loads(ai_raw)
                    print(f"  AI extracted {len(extracted_events)} items from {process_url}")
                    if extracted_events:
                        print(f"  Sample item: {extracted_events[0]}")

                    for event in extracted_events:
                        title = event.get('title', '')
                        event_url = event.get('url', '')
                        event_date = event.get('date') or ''
                        event_time = event.get('time') or '19:00'
                        recurring_pattern = event.get('recurring_pattern', '')

                        # Make URL absolute
                        if event_url and not event_url.startswith('http'):
                            from urllib.parse import urljoin
                            event_url = urljoin(url, event_url)
                        elif not event_url:
                            # If no specific event URL, use the main page URL
                            event_url = process_url

                        # Check if this needs Stage 2 scraping:
                        # - External URLs (not valdostacity.com) always need Stage 2
                        # - Internal event pages (/event/...) need Stage 2 for descriptions
                        # - Events without specific URLs (using main page URL) don't need Stage 2
                        needs_stage2 = event_url != process_url and event_url and ("valdostacity.com" not in event_url or "/event/" in event_url)

                        if title:
                            # Debug: check for suspicious titles
                            if title.lower() in ['unknown', 'untitled', 'tbd', 'tba']:
                                print(f"    ⚠️  WARNING: Suspicious title '{title}' extracted from {process_url}")

                            event_urls.append({
                                "title": title,
                                "url": event_url,
                                "has_external_url": needs_stage2,
                                "date": event_date,
                                "time": event_time,
                                "description": "",
                                "recurring_pattern": recurring_pattern  # Store recurring pattern from Stage 1
                            })
                            print(f"    Adding: {title} on {event_date}")
                            if recurring_pattern:
                                print(f"      Recurring: {recurring_pattern}")
                except Exception as e:
                    print(f"  Error parsing AI response: {e}")
                    continue
            else:
                # Structural parsing for visitvaldosta.org
                event_containers = soup.find_all("article", class_="event")
                print(f"[Two-Stage] Found {len(event_containers)} event containers")

                for container in event_containers:
                    try:
                        # Extract date (day number)
                        date_elem = container.find("div", class_="date")
                        day = date_elem.find("span").get_text(strip=True) if date_elem else None

                        # Extract month
                        txt_elem = container.find("div", class_="txt")
                        month_elem = txt_elem.find("span") if txt_elem else None
                        month = month_elem.get_text(strip=True) if month_elem else None

                        # Extract title from h3
                        title_elem = txt_elem.find("h3") if txt_elem else None
                        title = title_elem.get_text(strip=True) if title_elem else None

                        # Extract URL from parent <a> tag
                        parent_link = container.find_parent("a", href=True)
                        event_url = parent_link.get("href") if parent_link else None

                        # Extract time from description if available
                        desc_elem = container.find("p")
                        desc_text = desc_elem.get_text() if desc_elem else ""

                        # Look for time in description
                        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', desc_text, re.I)
                        if time_match:
                            hour = int(time_match.group(1))
                            minute = time_match.group(2)
                            am_pm = time_match.group(3).upper()
                            if am_pm == "PM" and hour != 12:
                                hour += 12
                            elif am_pm == "AM" and hour == 12:
                                hour = 0
                            event_time = f"{hour:02d}:{minute}"
                        else:
                            # Look for "Noon" or other time indicators
                            if "noon" in desc_text.lower():
                                event_time = "12:00"
                            else:
                                event_time = "19:00"

                        # Parse date
                        if day and month and title:
                            try:
                                # Convert month name to number
                                date_str = f"{day} {month} {current_year}"
                                parsed_date = dateparser.parse(date_str)
                                if parsed_date:
                                    # If date is in the past, assume next year
                                    if parsed_date.date() < datetime.now().date():
                                        parsed_date = parsed_date.replace(year=current_year + 1)

                                    formatted_date = parsed_date.strftime("%Y-%m-%d")

                                    # Check if URL is external (not visitvaldosta.org)
                                    has_external_url = event_url and "visitvaldosta.org" not in event_url if event_url else False

                                    # Debug: check for suspicious titles
                                    if title.lower() in ['unknown', 'untitled', 'tbd', 'tba']:
                                        print(f"[Two-Stage]   ⚠️  WARNING: Suspicious title '{title}' extracted!")

                                    event_data = {
                                        "title": title,
                                        "url": event_url or url,
                                        "has_external_url": has_external_url,
                                        "date": formatted_date,
                                        "time": event_time,
                                        "description": desc_text[:200] if desc_text else ""
                                    }
                                    event_urls.append(event_data)
                                    print(f"[Two-Stage]   Extracted: {title} on {formatted_date} at {event_time}")
                            except Exception as e:
                                print(f"[Two-Stage]   Error parsing date for {title}: {e}")
                                continue

                    except Exception as e:
                        print(f"[Two-Stage]   Error parsing container: {e}")
                        continue

                print(f"[Two-Stage] Stage 1: Successfully extracted {len(event_urls)} events using structural parsing")

        # After processing all URLs
        print(f"[Two-Stage] Stage 1 completed: {len(event_urls)} events extracted total")

        # Separate events into two groups:
        # 1. Events with external URLs - need Stage 2 scraping
        # 2. Events without external URLs - use dates from listing page
        events_with_external_urls = []
        events_without_external_urls = []
        seen_keys = set()  # Deduplicate by title + date

        for event in event_urls:
            event_title = event.get('title', 'Untitled')
            event_date = event.get('date', '')
            has_external_url = event.get('has_external_url', False)

            # Create deduplication key
            dedup_key = f"{event_title.lower().strip()}_{event_date}"

            if dedup_key in seen_keys:
                continue

            seen_keys.add(dedup_key)

            if has_external_url and event.get('url'):
                events_with_external_urls.append(event)
            else:
                events_without_external_urls.append(event)

        print(f"[Two-Stage] Stage 1: {len(events_with_external_urls)} events with external URLs, {len(events_without_external_urls)} events without")

        # Process events WITHOUT external URLs (use listing page dates)
        all_results = []
        for event in events_without_external_urls:
            event_title = event.get('title', 'Untitled')
            event_date = event.get('date') or ''
            event_time = event.get('time') or '19:00'
            event_url = event.get('url', url)  # Use listing page URL if no specific URL

            # Fix common typos in title
            if "Galentine's" in event_title or "galentine's" in event_title.lower():
                event_title = event_title.replace("Galentine's", "Valentine's").replace("galentine's", "Valentine's")

            # Validate date format
            try:
                parsed_date = datetime.fromisoformat(event_date).date()
                event_recurring = event.get('recurring_pattern', '')
                is_recurring = _is_supported_recurring_pattern(event_recurring)

                # Skip past dates UNLESS it's a supported recurring event
                if parsed_date >= datetime.now().date() or is_recurring:
                    # Validate time format
                    if not re.match(r'^\d{2}:\d{2}$', event_time):
                        event_time = '19:00'

                    result_item = {
                        "title": event_title,
                        "url": event_url,
                        "description": _truncate_description(event.get('description', '')),
                        "start": f"{event_date}T{event_time}:00",
                        "allDay": False,
                        "recurring_pattern": event_recurring  # Store recurring pattern if available
                    }
                    all_results.append(result_item)
                    if is_recurring:
                        print(f"[Two-Stage]   Added recurring event (no external URL): {event_title} on {event_date} (will expand)")
                    else:
                        print(f"[Two-Stage]   Added (no external URL): {event_title} on {event_date}")
            except Exception as e:
                print(f"[Two-Stage]   Skipping event with invalid date: {event_title} - {e}")
                continue

        # Stage 2: Scrape pages for events WITH external URLs
        if events_with_external_urls:
            print(f"[Two-Stage] Stage 2: Scraping {len(events_with_external_urls)} external event pages")

        for idx, event in enumerate(events_with_external_urls, 1):
            event_title = event.get('title', 'Untitled')
            event_url = event.get('url', '')
            listing_date = event.get('date', '')  # Date from Stage 1 (listing page)

            if not event_url:
                continue

            print(f"[Two-Stage] Stage 2 ({idx}/{len(events_with_external_urls)}): Scraping {event_title}")
            if listing_date:
                print(f"[Two-Stage]   Hint: Listing page showed date {listing_date}")

            try:
                # Fetch event page
                event_resp = requests.get(event_url, headers=headers, timeout=15)
                event_resp.raise_for_status()
                event_soup = BeautifulSoup(event_resp.text, "html.parser")

                # Remove script, style, nav, footer, and header elements
                for element in event_soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                # Get event page content
                event_content = str(event_soup.body)[:30000] if event_soup.body else str(event_soup)[:30000]

                # Stage 2 AI prompt - Use category-specific prompts
                today = datetime.now()
                six_months_later = today + timedelta(days=180)

                # Generate category-specific Stage 2 prompt
                if source_type == 'classes':
                    stage2_prompt = _generate_stage2_classes_prompt(event_title, event_content, listing_date, today, six_months_later)
                elif source_type == 'meetings':
                    stage2_prompt = _generate_stage2_meetings_prompt(event_title, event_content, listing_date, today, six_months_later)
                else:  # events (default)
                    stage2_prompt = _generate_stage2_events_prompt(event_title, event_content, listing_date, today, six_months_later)

                # Use GPT-4o-mini for Stage 2 (GPT-4o for Stage 1 is more critical)
                stage2_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": stage2_prompt}],
                    temperature=0.1
                )

                stage2_raw = stage2_response.choices[0].message.content.strip()

                # Clean JSON markers
                if stage2_raw.startswith("```json"):
                    stage2_raw = stage2_raw[7:]
                if stage2_raw.startswith("```"):
                    stage2_raw = stage2_raw[3:]
                if stage2_raw.endswith("```"):
                    stage2_raw = stage2_raw[:-3]
                stage2_raw = stage2_raw.strip()

                # Parse JSON
                try:
                    event_data = json.loads(stage2_raw)

                    status = event_data.get('status', 'unknown')
                    dates = event_data.get('dates', [])
                    time_str = event_data.get('time', '19:00')
                    raw_description = event_data.get('description', '')
                    description = _truncate_description(raw_description)
                    corrected_title = event_data.get('corrected_title', '')
                    recurring_pattern = event_data.get('recurring_pattern', '')

                    # Debug logging for description
                    if raw_description:
                        print(f"[Two-Stage]   AI extracted description ({len(raw_description)} chars): {raw_description[:80]}...")
                    else:
                        print(f"[Two-Stage]   AI returned empty description")

                    # Use corrected title if provided
                    if corrected_title and corrected_title.strip():
                        event_title = corrected_title.strip()

                    # Fix common typos in title
                    if "Galentine's" in event_title or "galentine's" in event_title.lower():
                        event_title = event_title.replace("Galentine's", "Valentine's").replace("galentine's", "Valentine's")
                        print(f"[Two-Stage]   Fixed typo: Galentine's → Valentine's")

                    # Skip cancelled/postponed events
                    if status in ['cancelled', 'postponed']:
                        print(f"[Two-Stage]   Skipping {event_title} - Status: {status}")
                        continue

                    # For internal valdostacity.com URLs, always use calendar dates (source of truth)
                    # For external URLs, prefer Stage 2 dates if found, otherwise use fallback
                    is_internal_valdosta = "valdostacity.com/event/" in event_url
                    fallback_date = event.get('date', '')
                    fallback_time = event.get('time', '19:00')

                    if is_internal_valdosta and fallback_date:
                        # Always use calendar dates for valdostacity.com internal pages
                        print(f"[Two-Stage]   Using calendar date for internal page: {event_title} on {fallback_date}")
                        dates = [fallback_date]
                        time_str = fallback_time
                    elif not dates:
                        # No dates in Stage 2, use fallback from Stage 1 (listing page)
                        if fallback_date:
                            print(f"[Two-Stage]   No dates in Stage 2, using fallback: {event_title} on {fallback_date}")
                            dates = [fallback_date]
                            time_str = fallback_time
                            # Use listing page description if Stage 2 description is empty
                            if not description:
                                description = _truncate_description(event.get('description', ''))
                        else:
                            print(f"[Two-Stage]   Skipping {event_title} - No dates found in Stage 2 or fallback")
                            continue

                    # Validate time format
                    if not re.match(r'^\d{2}:\d{2}$', time_str):
                        time_str = '19:00'

                    # Create calendar entry for EACH date (multi-day support)
                    for date_str in dates:
                        # Validate date format and ensure it's not in the past
                        # UNLESS it's a SUPPORTED recurring event (which will be expanded to future dates)
                        try:
                            event_date = datetime.fromisoformat(date_str).date()
                            is_recurring = _is_supported_recurring_pattern(recurring_pattern)

                            # Skip past dates UNLESS it's a supported recurring event
                            if event_date >= datetime.now().date() or is_recurring:
                                result_item = {
                                    "title": event_title,
                                    "url": event_url,
                                    "description": _truncate_description(description),
                                    "start": f"{date_str}T{time_str}:00",
                                    "allDay": False,
                                    "recurring_pattern": recurring_pattern  # Store recurring pattern for detection
                                }
                                all_results.append(result_item)
                                if is_recurring:
                                    print(f"[Two-Stage]   Added recurring event: {event_title} on {date_str} (will expand)")
                                else:
                                    print(f"[Two-Stage]   Added: {event_title} on {date_str}")
                            else:
                                print(f"[Two-Stage]   Skipping past date: {event_title} on {date_str}")
                        except Exception as e:
                            print(f"[Two-Stage]   Invalid date format: {date_str} - {e}")
                            continue

                except json.JSONDecodeError as e:
                    print(f"[Two-Stage]   ERROR: Failed to parse Stage 2 response for {event_title}: {e}")
                    print(f"[Two-Stage]   Raw output: {stage2_raw[:200]}...")
                    continue

                # Rate limiting: 1 second between requests
                if idx < len(events_with_external_urls):
                    time.sleep(1)

            except requests.exceptions.HTTPError as e:
                print(f"[Two-Stage]   HTTP error for {event_title}: {e.response.status_code}")
                # Fallback: Use listing page date
                fallback_date = event.get('date', '')
                fallback_time = event.get('time', '19:00')

                # Fix common typos in title
                fallback_title = event_title
                if "Galentine's" in fallback_title or "galentine's" in fallback_title.lower():
                    fallback_title = fallback_title.replace("Galentine's", "Valentine's").replace("galentine's", "Valentine's")

                if fallback_date:
                    try:
                        parsed_date = datetime.fromisoformat(fallback_date).date()
                        fallback_recurring = event.get('recurring_pattern', '')
                        is_recurring = _is_supported_recurring_pattern(fallback_recurring)

                        # Skip past dates UNLESS it's a supported recurring event
                        if parsed_date >= datetime.now().date() or is_recurring:
                            if not re.match(r'^\d{2}:\d{2}$', fallback_time):
                                fallback_time = '19:00'
                            fallback_desc = _truncate_description(event.get('description', ''))
                            result_item = {
                                "title": fallback_title,
                                "url": event_url,
                                "description": fallback_desc,
                                "start": f"{fallback_date}T{fallback_time}:00",
                                "allDay": False,
                                "recurring_pattern": fallback_recurring
                            }
                            all_results.append(result_item)
                            if is_recurring:
                                print(f"[Two-Stage]   Fallback: Added recurring event {fallback_title} on {fallback_date} (will expand)")
                            else:
                                print(f"[Two-Stage]   Fallback: Added {fallback_title} on {fallback_date} (from listing page)")
                    except Exception:
                        pass
                continue
            except requests.exceptions.Timeout:
                print(f"[Two-Stage]   Timeout for {event_title}")
                # Fallback: Use listing page date
                fallback_date = event.get('date', '')
                fallback_time = event.get('time', '19:00')

                # Fix common typos in title
                fallback_title = event_title
                if "Galentine's" in fallback_title or "galentine's" in fallback_title.lower():
                    fallback_title = fallback_title.replace("Galentine's", "Valentine's").replace("galentine's", "Valentine's")

                if fallback_date:
                    try:
                        parsed_date = datetime.fromisoformat(fallback_date).date()
                        fallback_recurring = event.get('recurring_pattern', '')
                        is_recurring = _is_supported_recurring_pattern(fallback_recurring)

                        # Skip past dates UNLESS it's a supported recurring event
                        if parsed_date >= datetime.now().date() or is_recurring:
                            if not re.match(r'^\d{2}:\d{2}$', fallback_time):
                                fallback_time = '19:00'
                            fallback_desc = _truncate_description(event.get('description', ''))
                            result_item = {
                                "title": fallback_title,
                                "url": event_url,
                                "description": fallback_desc,
                                "start": f"{fallback_date}T{fallback_time}:00",
                                "allDay": False,
                                "recurring_pattern": fallback_recurring
                            }
                            all_results.append(result_item)
                            if is_recurring:
                                print(f"[Two-Stage]   Fallback: Added recurring event {fallback_title} on {fallback_date} (will expand)")
                            else:
                                print(f"[Two-Stage]   Fallback: Added {fallback_title} on {fallback_date} (from listing page)")
                    except Exception:
                        pass
                continue
            except Exception as e:
                print(f"[Two-Stage]   Error scraping {event_title}: {e}")
                continue

        # Final deduplication based on URL + date + title
        # Include title to allow multiple events on same day at same venue
        print(f"[Two-Stage] Before final deduplication: {len(all_results)} events")
        deduplicated_results = []
        seen_keys = set()

        for event in all_results:
            event_date = event['start'].split('T')[0]
            event_url = event['url']
            event_title = event.get('title', '').lower()[:50]  # First 50 chars, lowercase
            # Create key from URL + date + title
            dedup_key = f"{event_url}_{event_date}_{event_title}"

            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                deduplicated_results.append(event)

        print(f"[Two-Stage] After final deduplication: {len(deduplicated_results)} events")

        # Expand recurring events
        expanded_results = _expand_recurring_events(deduplicated_results)
        print(f"[Two-Stage] After expanding recurring events: {len(expanded_results)} events")

        print(f"[Two-Stage] Completed: Found {len(expanded_results)} valid events")
        return expanded_results

    except Exception as e:
        print(f"[Two-Stage] ERROR in two-stage scraping: {e}")
        return []


def _is_supported_recurring_pattern(recurring_pattern: str) -> bool:
    """
    Check if a recurring pattern is actually supported for expansion.
    Only return True for patterns we can actually expand.
    """
    if not recurring_pattern:
        return False

    pattern_lower = recurring_pattern.lower()

    # Supported patterns
    supported = [
        'first friday', '1st friday',
        'second saturday', '2nd saturday',
        'third tuesday', '3rd tuesday',
    ]

    return any(p in pattern_lower for p in supported)


def _expand_recurring_events(results: List[Dict]) -> List[Dict]:
    """Detect and expand recurring events into multiple occurrences"""
    from dateutil.relativedelta import relativedelta
    from calendar import monthrange

    expanded = []
    for event in results:
        title = event.get('title', '').lower()
        # Handle None values for recurring_pattern
        recurring_pattern = (event.get('recurring_pattern') or '').lower()

        # Check both title AND recurring_pattern field for patterns
        search_text = f"{title} {recurring_pattern}"

        # Track if this is a recurring event
        is_recurring = False

        # Pattern 1: First Friday (or 1st Friday)
        if 'first friday' in search_text or '1st friday' in search_text:
            print(f"  [RECURRING] Detected 'First Friday' pattern: {event['title']}")
            if recurring_pattern:
                print(f"    Pattern field: {recurring_pattern}")
            is_recurring = True

            # Get the original event's time
            original_start = event.get('start', '')
            try:
                # Extract time from original event (default to 19:00)
                if 'T' in original_start:
                    event_time = original_start.split('T')[1]
                else:
                    event_time = '19:00:00'

                # Generate first Friday of each month for next 6 months
                current_date = datetime.now()
                for i in range(6):
                    target_month = current_date + relativedelta(months=i)
                    year = target_month.year
                    month = target_month.month

                    # Find first Friday of the month
                    # Get the first day of the month
                    first_day = datetime(year, month, 1)
                    # Friday is weekday 4 (0=Monday, 4=Friday)
                    days_until_friday = (4 - first_day.weekday()) % 7
                    first_friday = first_day + timedelta(days=days_until_friday)

                    # Only add if it's in the future
                    if first_friday.date() >= datetime.now().date():
                        recurring_event = event.copy()
                        recurring_event['start'] = f"{first_friday.strftime('%Y-%m-%d')}T{event_time}"
                        expanded.append(recurring_event)
                        print(f"    [RECURRING] Generated: {event['title']} on {first_friday.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"    [RECURRING] Error expanding: {e}")
                # If expansion fails, just add the original event
                expanded.append(event)

        # Pattern 2: Second Saturday (or 2nd Saturday)
        elif 'second saturday' in search_text or '2nd saturday' in search_text:
            print(f"  [RECURRING] Detected 'Second Saturday' pattern: {event['title']}")
            if recurring_pattern:
                print(f"    Pattern field: {recurring_pattern}")
            is_recurring = True

            original_start = event.get('start', '')
            try:
                if 'T' in original_start:
                    event_time = original_start.split('T')[1]
                else:
                    event_time = '19:00:00'

                current_date = datetime.now()
                for i in range(6):
                    target_month = current_date + relativedelta(months=i)
                    year = target_month.year
                    month = target_month.month

                    # Find second Saturday of the month
                    first_day = datetime(year, month, 1)
                    # Saturday is weekday 5
                    days_until_saturday = (5 - first_day.weekday()) % 7
                    first_saturday = first_day + timedelta(days=days_until_saturday)
                    second_saturday = first_saturday + timedelta(days=7)

                    if second_saturday.date() >= datetime.now().date():
                        recurring_event = event.copy()
                        recurring_event['start'] = f"{second_saturday.strftime('%Y-%m-%d')}T{event_time}"
                        expanded.append(recurring_event)
                        print(f"    [RECURRING] Generated: {event['title']} on {second_saturday.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"    [RECURRING] Error expanding: {e}")
                expanded.append(event)

        # Pattern 3: Third Tuesday (or 3rd Tuesday)
        elif 'third tuesday' in search_text or '3rd tuesday' in search_text:
            print(f"  [RECURRING] Detected 'Third Tuesday' pattern: {event['title']}")
            if recurring_pattern:
                print(f"    Pattern field: {recurring_pattern}")
            is_recurring = True

            original_start = event.get('start', '')
            try:
                if 'T' in original_start:
                    event_time = original_start.split('T')[1]
                else:
                    event_time = '19:00:00'

                current_date = datetime.now()
                for i in range(6):
                    target_month = current_date + relativedelta(months=i)
                    year = target_month.year
                    month = target_month.month

                    # Find third Tuesday of the month
                    first_day = datetime(year, month, 1)
                    # Tuesday is weekday 1
                    days_until_tuesday = (1 - first_day.weekday()) % 7
                    first_tuesday = first_day + timedelta(days=days_until_tuesday)
                    third_tuesday = first_tuesday + timedelta(days=14)

                    if third_tuesday.date() >= datetime.now().date():
                        recurring_event = event.copy()
                        recurring_event['start'] = f"{third_tuesday.strftime('%Y-%m-%d')}T{event_time}"
                        expanded.append(recurring_event)
                        print(f"    [RECURRING] Generated: {event['title']} on {third_tuesday.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f"    [RECURRING] Error expanding: {e}")
                expanded.append(event)

        # If not a recurring event, add as-is
        if not is_recurring:
            expanded.append(event)

    return expanded


def _post_process_ai_results(results: List[Dict], source_type: str, base_url: str) -> List[Dict]:
    """Apply post-processing to AI results for consistency and quality"""
    print(f"  Post-processing: Starting with {len(results)} items")
    processed = []

    for item in results:
        title = item.get('title', '')

        # Step 1: Category-specific title cleanup
        if source_type == 'events':
            # For events: Remove ordinals + "annual", year prefixes
            # Remove ordinal indicators (1st, 2nd, 3rd, 4th, etc.) with "annual"
            title = re.sub(r'^\d+(st|nd|rd|th)\s+annual\s+', '', title, flags=re.IGNORECASE)
            # Remove standalone "annual" at beginning
            title = re.sub(r'^annual\s+', '', title, flags=re.IGNORECASE)
            # Remove year prefixes like "2026"
            title = re.sub(r'^20\d{2}\s+', '', title)
            # Remove month names at the beginning
            title = re.sub(r'^(January|February|March|April|May|June|July|August|September|October|November|December)', '', title, flags=re.IGNORECASE)

        elif source_type == 'classes':
            # For classes: Keep ordinals (2nd Week, Week 3), don't remove year prefixes
            # Only remove leading bare numbers without ordinals
            if not re.match(r'^\d+(st|nd|rd|th)\s', title, re.IGNORECASE):
                if not re.match(r'^(week|session)\s+\d+', title, re.IGNORECASE):  # Keep "Week 3"
                    title = re.sub(r'^\d+\s+', '', title)  # Remove bare leading numbers only

        elif source_type == 'meetings':
            # For meetings: Keep everything including year prefixes (e.g., "2026 Annual Meeting")
            # Don't remove ordinals or year prefixes - meetings need precise names
            pass

        title = title.strip()

        # Step 2: Filter out junk titles (UI elements, navigation, etc.)
        junk_exact = ['log in', 'sign up', 'learn more', 'read more', 'click here',
                     'menu', 'search', 'home', 'about', 'contact', 'privacy',
                     'terms', 'getting there', 'share', 'save', 'map', 'photos']

        if title.lower() in junk_exact:
            continue

        # Step 3: Filter very short titles (but NOT duplicates - recurring events are OK!)
        if len(title) < 3:
            continue

        # Update the title in the item
        item['title'] = title
        processed.append(item)

    # Step 4: Category-specific date filtering
    if source_type == 'events':
        # Events: Filter out past dates
        current_date = datetime.now().date()
        before_filter = len(processed)
        filtered_events = []
        for r in processed:
            event_date = datetime.fromisoformat(r['start'].split('T')[0]).date()
            if event_date >= current_date:
                filtered_events.append(r)
            else:
                print(f"    Filtering past event: {r['title']} on {event_date}")
        processed = filtered_events
        if before_filter > len(processed):
            print(f"  Filtered out {before_filter - len(processed)} past events")

    elif source_type == 'classes':
        # Classes: DON'T filter past dates aggressively (might show recent history or ongoing classes)
        # Only filter dates more than 30 days in the past
        current_date = datetime.now().date()
        before_filter = len(processed)
        filtered_classes = []
        for r in processed:
            class_date = datetime.fromisoformat(r['start'].split('T')[0]).date()
            days_diff = (current_date - class_date).days
            if days_diff <= 30:  # Keep classes from last 30 days
                filtered_classes.append(r)
            else:
                print(f"    Filtering old class: {r['title']} on {class_date} ({days_diff} days ago)")
        processed = filtered_classes
        if before_filter > len(processed):
            print(f"  Filtered out {before_filter - len(processed)} old classes")

    elif source_type == 'meetings':
        # Meetings: Filter out past dates (like events)
        current_date = datetime.now().date()
        before_filter = len(processed)
        filtered_meetings = []
        for r in processed:
            meeting_date = datetime.fromisoformat(r['start'].split('T')[0]).date()
            if meeting_date >= current_date:
                filtered_meetings.append(r)
            else:
                print(f"    Filtering past meeting: {r['title']} on {meeting_date}")
        processed = filtered_meetings
        if before_filter > len(processed):
            print(f"  Filtered out {before_filter - len(processed)} past meetings")

    # Step 5: Deduplicate events on the same date with similar titles
    if source_type == 'events':
        deduplicated = []
        seen = set()

        for event in processed:
            event_date = event['start'].split('T')[0]
            # Normalize title for comparison
            normalized_title = ' '.join(event['title'].lower().split())
            # Create key from date + first 30 chars of normalized title
            key = f"{event_date}_{normalized_title[:30]}"

            if key not in seen:
                seen.add(key)
                deduplicated.append(event)

        if len(deduplicated) < len(processed):
            print(f"  Removed {len(processed) - len(deduplicated)} duplicate events")
        processed = deduplicated

    print(f"  Post-processing: Finished with {len(processed)} items")
    return processed


def scrape_generic_auto(url: str, source_type: str) -> List[Dict]:
    """Attempt generic scraping patterns (fallback when AI is not available)"""
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    try:
        # Use moderate headers - enough to bypass most blocks, but not so many as to trigger bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Try common patterns
        # Pattern 1: Look for calendar table
        calendar_table = soup.find("table")
        if calendar_table and source_type == 'events':
            # Try calendar table scraping - check current month and next 6 months

            current_date = datetime.now()
            months_to_check = [current_date + relativedelta(months=i) for i in range(7)]
            calendar_events_found = 0

            for month_date in months_to_check:
                month_str = month_date.strftime("%Y-%m")

                # Try both base URL and URL with month parameter
                urls_to_try = []
                # Only try base URL for current month
                if month_date.month == current_date.month and month_date.year == current_date.year:
                    urls_to_try.append(url)
                # For other months, use month parameter
                if '?' in url:
                    urls_to_try.append(f"{url.split('?')[0]}?month={month_str}")
                else:
                    urls_to_try.append(f"{url}?month={month_str}")

                for check_url in urls_to_try:
                    try:
                        month_resp = requests.get(check_url, headers=headers, timeout=10)
                        if month_resp.status_code == 200:
                            month_soup = BeautifulSoup(month_resp.text, "html.parser")
                            month_table = month_soup.find("table")

                            if month_table:
                                cells = month_table.find_all("td")
                                for cell in cells:
                                    links = cell.find_all("a", href=True)
                                    data_date = cell.get("data-date")

                                    if links and data_date:
                                        for link in links:
                                            event_text = link.get_text(strip=True)
                                            if event_text and len(event_text) > 3:
                                                event_url = link.get("href", "")
                                                if event_url.startswith("/"):
                                                    event_url = urljoin(url, event_url)

                                                cell_text = cell.get_text()
                                                time_str = extract_time(cell_text)

                                                # Check if already added (avoid duplicates)
                                                event_key = f"{event_text}_{data_date}"
                                                if not any(r.get('title') == event_text and r.get('start', '').startswith(data_date) for r in results):
                                                    results.append({
                                                        "title": event_text,
                                                        "url": event_url,
                                                        "description": "",
                                                        "start": f"{data_date}T{time_str}:00",
                                                        "allDay": False
                                                    })
                                                    calendar_events_found += 1
                                break  # Found table for this URL pattern, move to next month
                    except Exception as e:
                        continue  # Try next URL pattern

            if calendar_events_found > 0:
                print(f"  Calendar table found {calendar_events_found} events across multiple months before filtering")

        # Pattern 2: Look for article/event/place containers (with broader patterns)
        if not results:
            # Enhanced pattern to catch more variations: PlaceView, EventCard, etc.
            containers = soup.find_all(["article", "div", "li", "section"],
                                      class_=re.compile(r"event|attraction|place|card|item|entry|post|listing|view", re.I))
            seen_titles = set()  # Track seen titles to avoid duplicates
            raw_count = len(containers)
            filtered_count = 0

            for container in containers:  # No limit - scrape all items found
                title_elem = container.find(["h2", "h3", "h4", "a"])
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Clean up title - remove leading numbers, dates, etc.
                title = re.sub(r'^\d+\s*', '', title)  # Remove leading numbers
                title = re.sub(r'^\d{1,2}[A-Za-z]+', '', title)  # Remove date prefixes like "13November"
                # Remove month names at the beginning (like "NovemberEvent Name")
                title = re.sub(r'^(January|February|March|April|May|June|July|August|September|October|November|December)', '', title, flags=re.IGNORECASE)
                title = title.strip()

                # Filter out junk titles (UI elements, navigation, etc.) - only exact matches
                junk_exact = ['log in', 'sign up', 'learn more', 'read more', 'click here',
                             'menu', 'search', 'home', 'about', 'contact', 'privacy',
                             'terms', 'getting there', 'share', 'save', 'map', 'photos']

                # Only filter if it's an EXACT match to junk keywords
                if title.lower() in junk_exact:
                    continue

                # Very minimal filtering - only remove very short titles and duplicates
                if len(title) < 3 or title.lower() in seen_titles:
                    continue

                seen_titles.add(title.lower())

                # Get URL
                link = container.find("a", href=True)
                item_url = link.get("href", url) if link else url
                if item_url.startswith("/"):
                    item_url = urljoin(url, item_url)

                # Get description
                desc_elem = container.find("p")
                description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

                # For events, try to find date
                if source_type == 'events':
                    # Try multiple strategies to extract date
                    dt = None
                    date_text = ""

                    # Strategy 1: Look for time/date elements
                    date_elem = container.find(["time", "span", "div"], class_=re.compile(r"date|time", re.I))
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)

                    # Strategy 2: Look for month names in nearby text (handles split date formats)
                    if not date_text or len(date_text) < 3:
                        # Search for month names in the container
                        container_text = container.get_text()
                        month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', container_text, re.I)
                        if month_match:
                            month_name = month_match.group(1)
                            # Try to find a day number nearby
                            day_match = re.search(r'\b(\d{1,2})\b', container_text)
                            if day_match:
                                day_num = day_match.group(1)
                                date_text = f"{month_name} {day_num}"

                    # Parse the date
                    if date_text:
                        try:
                            dt = dateparser.parse(date_text)
                            if dt:
                                # If the parsed date is in the past, assume it's for next year
                                if dt.date() < datetime.now().date():
                                    dt = dt.replace(year=dt.year + 1)

                                date_str = dt.strftime("%Y-%m-%d")
                                time_str = extract_time(container_text)
                                results.append({
                                    "title": title,
                                    "url": item_url,
                                    "description": description,
                                    "start": f"{date_str}T{time_str}:00",
                                    "allDay": False
                                })
                                filtered_count += 1
                        except Exception as e:
                            pass
                else:
                    # For attractions
                    today = datetime.now().strftime("%Y-%m-%d")
                    import random
                    time_str = f"{random.randint(9, 17):02d}:00"

                    # Don't add "Visit:" prefix if title already has it
                    display_title = title if title.startswith(("Visit:", "Visit ")) else title

                    results.append({
                        "title": display_title,
                        "url": item_url,
                        "description": description,
                        "start": f"{today}T{time_str}:00",
                        "allDay": False
                    })
                    filtered_count += 1

            # Log filtering statistics for debugging
            if raw_count > 0:
                print(f"  Filtering: {raw_count} containers → {filtered_count} valid items")

        # Pattern 3: Fallback for article-style pages with h2/h3/h4 headers (like Explore Georgia)
        # Use this when we haven't found many results and we're looking for attractions
        if source_type == 'attractions' and len(results) < 20:
            article_headers = soup.find_all(["h2", "h3", "h4"])
            seen_titles_article = {r['title'].lower() for r in results}  # Track already found

            for header in article_headers:
                title = header.get_text(strip=True)

                # Skip if title is too short or looks like a section header
                if len(title) < 3 or title.lower() in ["things to do", "attractions", "events", "overview", "about"]:
                    continue

                # Skip if already found
                if title.lower() in seen_titles_article:
                    continue

                seen_titles_article.add(title.lower())

                # Find the following paragraph for description
                description = ""
                next_elem = header.find_next_sibling(["p", "div"])
                if next_elem:
                    description = next_elem.get_text(strip=True)[:200]

                # Try to find a link
                link = header.find("a") or (next_elem.find("a") if next_elem else None)
                attraction_url = urljoin(url, link["href"]) if link and link.get("href") else url

                results.append({
                    "title": title,
                    "url": attraction_url,
                    "description": description,
                    "start": datetime.now().strftime("%Y-%m-%dT10:00:00"),
                    "allDay": False
                })

            if len(article_headers) > 0:
                print(f"  Article-style fallback pattern found {len(article_headers)} headers, added {len(results) - filtered_count} new items")

        # Filter out past events
        if source_type == 'events':
            before_filter = len(results)
            current_date = datetime.now().date()
            results = [r for r in results if datetime.fromisoformat(r['start'].split('T')[0]).date() >= current_date]
            if before_filter > len(results):
                print(f"  Filtered out {before_filter - len(results)} past events (before: {before_filter}, after: {len(results)})")

        # Deduplicate events on the same date with similar titles
        if source_type == 'events':
            deduplicated = []
            seen = set()

            for event in results:
                event_date = event['start'].split('T')[0]
                # Normalize title for comparison (lowercase, remove extra spaces)
                normalized_title = ' '.join(event['title'].lower().split())
                # Create key from date + first 30 chars of normalized title
                key = f"{event_date}_{normalized_title[:30]}"

                if key not in seen:
                    seen.add(key)
                    deduplicated.append(event)

            if len(deduplicated) < len(results):
                print(f"  Removed {len(results) - len(deduplicated)} duplicate events")
            results = deduplicated

        print(f"Generic auto scraping found {len(results)} items from {url}")
        return results

    except Exception as e:
        print(f"Error in generic auto scraping for {url}: {e}")
        return []


def extract_time(text: str) -> str:
    """Extract time from text, return HH:MM format"""
    time_patterns = [
        r'(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)',
        r'(\d{1,2})\s*(?:AM|PM|am|pm)',
    ]

    for pattern in time_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                if len(match.groups()) == 2:
                    hour, minute = match.groups()
                    hour_int = int(hour)
                    if 'PM' in match.group(0).upper() and hour_int != 12:
                        hour_int += 12
                    elif 'AM' in match.group(0).upper() and hour_int == 12:
                        hour_int = 0
                    return f"{hour_int:02d}:{minute}"
                else:
                    hour = match.group(1)
                    hour_int = int(hour)
                    if 'PM' in match.group(0).upper() and hour_int != 12:
                        hour_int += 12
                    elif 'AM' in match.group(0).upper() and hour_int == 12:
                        hour_int = 0
                    return f"{hour_int:02d}:00"
            except (ValueError, IndexError):
                pass

    # Default times based on context
    import random
    text_lower = text.lower()
    if any(word in text_lower for word in ["morning", "breakfast", "brunch"]):
        return f"{random.randint(8, 11):02d}:00"
    elif any(word in text_lower for word in ["lunch", "noon", "afternoon"]):
        return f"{random.randint(12, 14):02d}:00"
    elif any(word in text_lower for word in ["evening", "dinner", "night"]):
        return f"{random.randint(18, 21):02d}:00"
    else:
        return f"{random.randint(10, 17):02d}:00"
