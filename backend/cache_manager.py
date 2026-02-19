"""
Cache Manager - Handles on-demand caching of scraped data
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Auto-detect cache directory
# HF Spaces provides /data for persistent storage, otherwise use backend/cache/
if os.path.exists('/data'):
    CACHE_DIR = '/data/cache'
else:
    CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache validity period (24 hours)
CACHE_VALIDITY_HOURS = 24


def get_cache_file_path(cache_type: str) -> str:
    """Get the cache file path for a given type"""
    return os.path.join(CACHE_DIR, f'{cache_type}_cache.json')


def is_cache_valid(cache_type: str) -> bool:
    """Check if cache exists and is still valid (< 24 hours old)"""
    cache_file = get_cache_file_path(cache_type)

    if not os.path.exists(cache_file):
        return False

    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        timestamp_str = cache_data.get('timestamp')
        if not timestamp_str:
            return False

        # Parse timestamp and check age
        cache_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age_hours = (datetime.now(cache_time.tzinfo) - cache_time).total_seconds() / 3600

        return age_hours < CACHE_VALIDITY_HOURS

    except Exception as e:
        print(f"Error checking cache validity: {e}")
        return False


def load_from_cache(cache_type: str) -> Optional[List[Dict]]:
    """Load data from cache if valid"""
    if not is_cache_valid(cache_type):
        return None

    try:
        cache_file = get_cache_file_path(cache_type)
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        print(f"  [CACHE] Loading {cache_type} from cache (age: {get_cache_age_hours(cache_type):.1f}h)")
        return cache_data.get('data', [])

    except Exception as e:
        print(f"Error loading from cache: {e}")
        return None


def save_to_cache(cache_type: str, data: List[Dict]) -> None:
    """Save data to cache with timestamp"""
    try:
        cache_file = get_cache_file_path(cache_type)
        cache_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'data': data,
            'count': len(data)
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        print(f"  [CACHE] Saved {len(data)} items to {cache_type} cache")

    except Exception as e:
        print(f"Error saving to cache: {e}")


def get_cache_age_hours(cache_type: str) -> float:
    """Get the age of the cache in hours"""
    cache_file = get_cache_file_path(cache_type)

    if not os.path.exists(cache_file):
        return float('inf')

    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        timestamp_str = cache_data.get('timestamp')
        if not timestamp_str:
            return float('inf')

        cache_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return (datetime.now(cache_time.tzinfo) - cache_time).total_seconds() / 3600

    except Exception as e:
        print(f"Error getting cache age: {e}")
        return float('inf')


def clear_cache(cache_type: str) -> bool:
    """Clear cache for a specific type"""
    try:
        cache_file = get_cache_file_path(cache_type)
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"  [CACHE] Cleared {cache_type} cache")
            return True
        return False
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return False
