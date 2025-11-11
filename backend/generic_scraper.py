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


def scrape_with_custom_selectors(url: str, selectors: Dict, source_type: str, headers: Dict) -> List[Dict]:
    """Scrape using user-provided CSS selectors"""
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []

        # Handle calendar table format (like valdostamainstreet.com)
        if 'calendar_table' in selectors:
            results = scrape_calendar_table(url, soup, selectors)
        # Handle generic list format
        elif 'item_container' in selectors:
            results = scrape_list_format(url, soup, selectors, source_type)
        else:
            print(f"Unknown selector format for {url}")

        return results

    except Exception as e:
        print(f"Error scraping {url} with custom selectors: {e}")
        return []


def scrape_calendar_table(url: str, soup: BeautifulSoup, selectors: Dict) -> List[Dict]:
    """Scrape calendar table format"""
    events = []

    # Handle multi-month calendars (like valdostamainstreet.com)
    base_url = url.split('?')[0]
    months_to_scrape = []

    if "?month=" not in url:
        # Scrape current and next 2 months
        current_date = datetime.now()
        for month_offset in range(3):
            year = current_date.year
            month = current_date.month + month_offset
            while month > 12:
                month -= 12
                year += 1
            month_url = f"{base_url}?month={year}-{month:02d}"
            months_to_scrape.append(month_url)
    else:
        months_to_scrape = [url]

    for month_url in months_to_scrape:
        try:
            if month_url != url:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                resp = requests.get(month_url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.select_one(selectors.get('calendar_table', 'table'))
            if not table:
                continue

            # Find all event cells
            event_cells = table.select(selectors.get('event_cell', 'td'))

            for cell in event_cells:
                # Find event links in this cell
                event_links = cell.select(selectors.get('event_link', 'a'))

                if not event_links:
                    continue

                # Get date from attribute
                date_attr = selectors.get('date_attribute', 'data-date')
                date_str = cell.get(date_attr)

                if not date_str:
                    continue

                # Parse date
                try:
                    dt = dateparser.parse(date_str)
                    if not dt:
                        continue
                    date_iso = dt.strftime("%Y-%m-%d")
                except Exception:
                    continue

                # Process each event link
                for link in event_links:
                    event_text = link.get_text(strip=True)
                    if not event_text or len(event_text) < 3:
                        continue

                    event_url = link.get("href", "")
                    if event_url.startswith("/"):
                        event_url = urljoin(url, event_url)

                    # Extract time from cell text
                    cell_text = cell.get_text()
                    time_str = extract_time(cell_text)

                    events.append({
                        "title": event_text,
                        "url": event_url,
                        "description": "",
                        "start": f"{date_iso}T{time_str}:00",
                        "allDay": False
                    })

        except Exception as e:
            print(f"Error processing calendar month {month_url}: {e}")
            continue

    # Filter past events
    current_date = datetime.now().date()
    filtered_events = [e for e in events if datetime.fromisoformat(e['start'].split('T')[0]).date() >= current_date]

    return filtered_events


def scrape_list_format(url: str, soup: BeautifulSoup, selectors: Dict, source_type: str) -> List[Dict]:
    """Scrape list/grid format (for attractions or event lists)"""
    results = []

    # Find all item containers
    items = soup.select(selectors.get('item_container', 'article'))

    for item in items:
        try:
            # Extract title
            title_elem = item.select_one(selectors.get('title_selector', 'h2, h3'))
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)

            # Extract URL
            link_elem = item.select_one(selectors.get('link_selector', 'a'))
            item_url = link_elem.get('href', url) if link_elem else url
            if item_url.startswith('/'):
                item_url = urljoin(url, item_url)

            # Extract description
            desc_elem = item.select_one(selectors.get('description_selector', 'p'))
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            if source_type == 'events':
                # Extract date for events
                date_elem = item.select_one(selectors.get('date_selector', 'time, .date'))
                if date_elem:
                    date_text = date_elem.get_text()
                    try:
                        dt = dateparser.parse(date_text)
                        if dt:
                            date_str = dt.strftime("%Y-%m-%d")
                            time_str = extract_time(date_text)
                            results.append({
                                "title": title,
                                "url": item_url,
                                "description": description[:200],
                                "start": f"{date_str}T{time_str}:00",
                                "allDay": False
                            })
                    except Exception:
                        pass
            else:
                # For attractions, use today's date
                today = datetime.now().strftime("%Y-%m-%d")
                import random
                time_str = f"{random.randint(9, 17):02d}:00"

                results.append({
                    "title": f"Visit: {title}",
                    "url": item_url,
                    "description": description[:200],
                    "start": f"{today}T{time_str}:00",
                    "allDay": False
                })

        except Exception as e:
            print(f"Error parsing item: {e}")
            continue

    return results


def scrape_with_ai(url: str, source_type: str, openai_client: Optional[OpenAI]) -> List[Dict]:
    """Use AI to intelligently scrape any website"""
    if not openai_client:
        print(f"OpenAI client not available for AI scraping {url}")
        return []

    try:
        # Fetch the page
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text content (limited to avoid token limits)
        text_content = soup.get_text()[:15000]  # Limit to ~15k chars

        # Use AI to extract events/attractions
        prompt = f"""
You are an expert web scraper. Extract {source_type} information from the following webpage content.

For each item, provide:
- title: The name of the {source_type[:-1]}
- date: The date (YYYY-MM-DD format) if this is an event, or today's date if it's an attraction
- time: The time (HH:MM format) if available, otherwise "10:00" for attractions or "19:00" for events
- description: A brief description (1-2 sentences max)
- url: The full URL if found in the content, otherwise use "{url}"

Return ONLY a JSON array with no additional text. Format:
[
  {{"title": "Event Name", "date": "2025-01-15", "time": "19:00", "description": "Description here", "url": "{url}"}},
  ...
]

Webpage content:
{text_content}
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

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
        items = json.loads(raw_output)

        # Format results
        results = []
        for item in items:
            date_str = item.get('date', datetime.now().strftime("%Y-%m-%d"))
            time_str = item.get('time', '10:00')

            results.append({
                "title": item.get('title', 'Untitled'),
                "url": item.get('url', url),
                "description": item.get('description', ''),
                "start": f"{date_str}T{time_str}:00",
                "allDay": False
            })

        print(f"AI extracted {len(results)} items from {url}")
        return results

    except Exception as e:
        print(f"Error in AI scraping for {url}: {e}")
        return []


def scrape_generic_auto(url: str, source_type: str) -> List[Dict]:
    """Attempt generic scraping patterns (fallback when AI is not available)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Try common patterns
        # Pattern 1: Look for calendar table
        calendar_table = soup.find("table")
        if calendar_table and source_type == 'events':
            # Try calendar table scraping
            cells = calendar_table.find_all("td")
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

                            results.append({
                                "title": event_text,
                                "url": event_url,
                                "description": "",
                                "start": f"{data_date}T{time_str}:00",
                                "allDay": False
                            })

        # Pattern 2: Look for article/event containers
        if not results:
            containers = soup.find_all(["article", "div"], class_=re.compile(r"event|attraction|place", re.I))
            for container in containers[:20]:  # Limit to 20 items
                title_elem = container.find(["h2", "h3", "h4", "a"])
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if len(title) < 3:
                    continue

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
                    date_elem = container.find(["time", "span", "div"], class_=re.compile(r"date|time", re.I))
                    if date_elem:
                        date_text = date_elem.get_text()
                        try:
                            dt = dateparser.parse(date_text)
                            if dt:
                                date_str = dt.strftime("%Y-%m-%d")
                                time_str = extract_time(date_text)
                                results.append({
                                    "title": title,
                                    "url": item_url,
                                    "description": description,
                                    "start": f"{date_str}T{time_str}:00",
                                    "allDay": False
                                })
                        except Exception:
                            pass
                else:
                    # For attractions
                    today = datetime.now().strftime("%Y-%m-%d")
                    import random
                    time_str = f"{random.randint(9, 17):02d}:00"

                    results.append({
                        "title": f"Visit: {title}",
                        "url": item_url,
                        "description": description,
                        "start": f"{today}T{time_str}:00",
                        "allDay": False
                    })

        # Filter past events
        if source_type == 'events':
            current_date = datetime.now().date()
            results = [r for r in results if datetime.fromisoformat(r['start'].split('T')[0]).date() >= current_date]

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
