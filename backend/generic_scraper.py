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


def scrape_with_ai(url: str, source_type: str, openai_client: Optional[OpenAI]) -> List[Dict]:
    """Use AI to intelligently scrape any website with post-processing for consistency"""
    if not openai_client:
        print(f"OpenAI client not available for AI scraping {url}")
        return []

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

                # Use AI to extract events/attractions
                current_year = datetime.now().year
                current_month = datetime.now().month

                # Create source-type specific prompts
                if source_type == 'events':
                    prompt = f"""
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


def _post_process_ai_results(results: List[Dict], source_type: str, base_url: str) -> List[Dict]:
    """Apply post-processing to AI results for consistency and quality"""
    print(f"  Post-processing: Starting with {len(results)} items")
    processed = []

    for item in results:
        title = item.get('title', '')

        # Step 1: Clean up title - remove leading numbers, dates, etc.
        title = re.sub(r'^\d+\s*', '', title)  # Remove leading numbers
        title = re.sub(r'^\d{1,2}[A-Za-z]+', '', title)  # Remove date prefixes like "13November"
        # Remove month names at the beginning
        title = re.sub(r'^(January|February|March|April|May|June|July|August|September|October|November|December)', '', title, flags=re.IGNORECASE)
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

    # Step 4: Filter out past events
    if source_type == 'events':
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
