"""
Source Manager - Handles loading, saving, and managing event/attraction sources
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import hashlib

SOURCES_FILE = os.path.join(os.path.dirname(__file__), 'sources.json')


def load_sources() -> Dict:
    """Load sources from JSON file"""
    if not os.path.exists(SOURCES_FILE):
        # Create default sources file
        default_data = {
            "sources": [],
            "settings": {
                "passcode_hash": hash_passcode("ovl4you"),  # Default passcode
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }
        save_sources(default_data)
        return default_data

    with open(SOURCES_FILE, 'r') as f:
        return json.load(f)


def save_sources(data: Dict) -> None:
    """Save sources to JSON file"""
    data['settings']['last_updated'] = datetime.utcnow().isoformat() + "Z"
    with open(SOURCES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_all_sources() -> List[Dict]:
    """Get all sources"""
    data = load_sources()
    return data.get('sources', [])


def get_enabled_sources() -> List[Dict]:
    """Get only enabled sources"""
    all_sources = get_all_sources()
    return [s for s in all_sources if s.get('enabled', True)]


def get_sources_by_type(source_type: str) -> List[Dict]:
    """Get enabled sources filtered by type (events or attractions)"""
    enabled_sources = get_enabled_sources()
    return [s for s in enabled_sources if s.get('type') == source_type]


def get_source_by_id(source_id: str) -> Optional[Dict]:
    """Get a specific source by ID"""
    all_sources = get_all_sources()
    for source in all_sources:
        if source.get('id') == source_id:
            return source
    return None


def is_blocked_url(url: str) -> bool:
    """Check if URL is blocked due to scraping restrictions"""
    blocked_domains = [
        'tripadvisor.com',
        'tripadvisor.',  # Catches all TripAdvisor subdomains
    ]

    url_lower = url.lower()
    for domain in blocked_domains:
        if domain in url_lower:
            return True
    return False


def add_source(source: Dict) -> Dict:
    """Add a new source"""
    # Check if URL is blocked
    url = source.get('url', '')
    if is_blocked_url(url):
        raise ValueError("This source is not supported due to scraping restrictions. Please use an alternative source.")

    data = load_sources()
    sources = data.get('sources', [])

    # Generate new ID
    max_id = 0
    for s in sources:
        try:
            sid = int(s.get('id', 0))
            if sid > max_id:
                max_id = sid
        except (ValueError, TypeError):
            pass

    source['id'] = str(max_id + 1)
    source['added_date'] = datetime.utcnow().isoformat() + "Z"

    # Set defaults
    if 'enabled' not in source:
        source['enabled'] = True
    if 'scraping_method' not in source:
        source['scraping_method'] = 'auto'

    sources.append(source)
    data['sources'] = sources
    save_sources(data)

    return source


def update_source(source_id: str, updates: Dict) -> Optional[Dict]:
    """Update an existing source"""
    # Check if trying to update URL to a blocked domain
    if 'url' in updates and is_blocked_url(updates['url']):
        raise ValueError("This source is not supported due to scraping restrictions. Please use an alternative source.")

    data = load_sources()
    sources = data.get('sources', [])

    for i, source in enumerate(sources):
        if source.get('id') == source_id:
            # Update fields
            for key, value in updates.items():
                if key != 'id' and key != 'added_date':  # Protect these fields
                    source[key] = value

            sources[i] = source
            data['sources'] = sources
            save_sources(data)
            return source

    return None


def delete_source(source_id: str) -> bool:
    """Delete a source"""
    data = load_sources()
    sources = data.get('sources', [])

    original_length = len(sources)
    sources = [s for s in sources if s.get('id') != source_id]

    if len(sources) < original_length:
        data['sources'] = sources
        save_sources(data)
        return True

    return False


def hash_passcode(passcode: str) -> str:
    """Hash a passcode using SHA-256"""
    return hashlib.sha256(passcode.encode()).hexdigest()


def verify_passcode(passcode: str) -> bool:
    """Verify a passcode against the stored hash"""
    data = load_sources()
    stored_hash = data.get('settings', {}).get('passcode_hash', '')
    return hash_passcode(passcode) == stored_hash


def update_passcode(new_passcode: str) -> None:
    """Update the passcode"""
    data = load_sources()
    if 'settings' not in data:
        data['settings'] = {}
    data['settings']['passcode_hash'] = hash_passcode(new_passcode)
    save_sources(data)
