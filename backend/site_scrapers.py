# backend/site_scrapers.py
"""
Site-specific scrapers for sources that require specialized parsing logic.
This module provides reusable scraping functions that can be configured per-source.
"""
import requests
import re
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin


def scrape_visitvaldosta_events(url: str) -> List[Dict]:
    """Specialized scraper for visitvaldosta.org events"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []

        # Find event containers
        event_containers = soup.find_all("article", class_=re.compile(r"event", re.I))

        for container in event_containers:
            try:
                # Extract title
                title_elem = container.find(["h2", "h3", "h4"])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Extract URL
                link = container.find("a", href=True)
                event_url = urljoin(url, link["href"]) if link else url

                # Extract description
                desc_elem = container.find("p")
                description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

                # Extract date/time - visitvaldosta has day and month in separate elements
                day_elem = container.find("div", class_="date")
                month_elem = container.find("div", class_="txt")

                if day_elem and month_elem:
                    day_span = day_elem.find("span")
                    month_span = month_elem.find("span")

                    if day_span and month_span:
                        day = day_span.get_text(strip=True)
                        month = month_span.get_text(strip=True)
                        date_text = f"{month} {day}"

                        # Parse the date
                        dt = dateparser.parse(date_text)
                        if dt:
                            # If the parsed date is in the past, assume it's for next year
                            if dt.date() < datetime.now().date():
                                dt = dt.replace(year=dt.year + 1)

                            # Only include events within the next year
                            if dt.date() <= (datetime.now() + timedelta(days=365)).date():
                                events.append({
                                    "title": title,
                                    "url": event_url,
                                    "description": description,
                                    "start": dt.strftime("%Y-%m-%dT%H:%M:%S"),
                                    "allDay": False
                                })
            except Exception as e:
                print(f"Error parsing event container: {e}")
                continue

        print(f"visitvaldosta scraper found {len(events)} events")
        return events

    except Exception as e:
        print(f"Error scraping visitvaldosta: {e}")
        return []


def scrape_wanderlog_attractions(url: str) -> List[Dict]:
    """Specialized scraper for wanderlog.com attractions"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        attractions = []

        # Wanderlog uses div.PlaceView__selectable for each attraction
        place_views = soup.find_all("div", class_="PlaceView__selectable")

        for place_view in place_views:
            try:
                # Extract title from h2
                title_elem = place_view.find("h2")
                if not title_elem:
                    continue
                title_link = title_elem.find("a")
                title = title_link.get_text(strip=True) if title_link else title_elem.get_text(strip=True)

                # Extract URL
                attraction_url = title_link["href"] if title_link and title_link.get("href") else url
                if attraction_url.startswith("/"):
                    attraction_url = urljoin(url, attraction_url)

                # Extract description
                desc_elem = place_view.find("div", class_="mt-2")
                description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

                attractions.append({
                    "title": title,
                    "url": attraction_url,
                    "description": description,
                    "start": datetime.now().strftime("%Y-%m-%dT10:00:00"),
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing Wanderlog attraction: {e}")
                continue

        print(f"wanderlog scraper found {len(attractions)} attractions")
        return attractions

    except Exception as e:
        print(f"Error scraping wanderlog: {e}")
        return []


def scrape_exploregeorgia_attractions(url: str) -> List[Dict]:
    """Specialized scraper for exploregeorgia.org attractions"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        attractions = []

        # Find all h2/h3/h4 headers in article content
        attraction_headers = soup.find_all(["h2", "h3", "h4"])

        for header in attraction_headers:
            try:
                title = header.get_text(strip=True)

                # Skip if title is too short or looks like a section header
                if len(title) < 3 or title.lower() in ["things to do", "attractions", "events"]:
                    continue

                # Find the following paragraph for description
                description = ""
                next_elem = header.find_next_sibling(["p", "div"])
                if next_elem:
                    description = next_elem.get_text(strip=True)[:200]

                # Try to find a link
                link = header.find("a") or (next_elem.find("a") if next_elem else None)
                attraction_url = urljoin(url, link["href"]) if link and link.get("href") else url

                attractions.append({
                    "title": title,
                    "url": attraction_url,
                    "description": description,
                    "start": datetime.now().strftime("%Y-%m-%dT10:00:00"),
                    "allDay": False
                })
            except Exception as e:
                print(f"Error parsing Explore Georgia attraction: {e}")
                continue

        print(f"exploregeorgia scraper found {len(attractions)} attractions")
        return attractions

    except Exception as e:
        print(f"Error scraping exploregeorgia: {e}")
        return []


# Registry of site-specific scrapers
SITE_SCRAPERS = {
    "visitvaldosta_events": scrape_visitvaldosta_events,
    "wanderlog_attractions": scrape_wanderlog_attractions,
    "exploregeorgia_attractions": scrape_exploregeorgia_attractions,
}


def get_site_scraper(scraper_name: str):
    """Get a site-specific scraper function by name"""
    return SITE_SCRAPERS.get(scraper_name)
