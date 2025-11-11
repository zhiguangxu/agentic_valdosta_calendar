# 🎉 Agentic Calendar - Major Upgrade Guide

## What's New?

The app has been completely refactored to support **user-configurable event sources**! You can now:

✅ Add/remove/modify event sources through a web interface
✅ Scrape events from **any website** (not just hardcoded ones)
✅ Use AI-powered intelligent scraping
✅ Configure custom CSS selectors for advanced scraping
✅ Passcode-protected settings page

---

## 🏗️ Architecture Changes

### Before (Old System)
- **Hardcoded** `APPROVED_SITES` array in `main.py`
- Site-specific scraping logic with multiple `if` statements
- No way to add new sources without code changes

### After (New System)
- **Dynamic** source management via `sources.json`
- **Generic** scraping engine that works with any website
- **Settings page** for managing sources (no code changes needed!)
- **Three scraping methods**:
  1. **Auto-detect**: Automatically finds events/attractions
  2. **AI-powered**: Uses GPT to intelligently extract content
  3. **Custom selectors**: Advanced users can specify CSS selectors

---

## 📁 New Files

### Backend
- `backend/sources.json` - Stores all configured sources (user-editable)
- `backend/source_manager.py` - Manages loading/saving sources
- `backend/generic_scraper.py` - Generic scraping engine
- `backend/main_backup.py` - Backup of old main.py

### Frontend
- `frontend/src/Settings.js` - New settings page component

### Modified Files
- `backend/main.py` - Refactored to use generic scraper
- `frontend/src/App.js` - Added settings button and navigation

---

## 🚀 Quick Start

### 1. Install Dependencies (if needed)
```bash
# Backend (if not installed)
pip install fastapi uvicorn openai requests beautifulsoup4 python-dateutil

# Frontend (if not installed)
cd frontend && npm install
```

### 2. Start the Application

**Terminal 1 - Backend:**
```bash
# From project root directory
uv run uvicorn backend.main:app --reload --port 8000

# OR if not using uv:
# python3 -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

**Important:** Always run the backend command from the **project root directory** (not from inside the backend folder).

### 3. Access Settings
1. Open http://localhost:3000
2. Click the **⚙️ Settings** button (top-right corner)
3. Enter passcode: **`admin123`** (default)
4. Manage your event sources!

---

## ⚙️ Using the Settings Page

### Adding a New Source

1. Click **"+ Add New Source"**
2. Fill in the form:
   - **Name**: A friendly name (e.g., "City Events Calendar")
   - **URL**: The website URL to scrape
   - **Type**: Choose "Events" or "Attractions"
   - **Scraping Method**:
     - `Auto-detect`: Let the system figure it out (recommended)
     - `AI-powered`: Use GPT for smart extraction (requires OpenAI API key)
     - `Calendar Table`: For calendar table formats (like valdostamainstreet.com)
   - **Enabled**: Check to enable this source
3. Click **"Add Source"**

### Editing a Source
1. Click **✏️ Edit** on any source
2. Update the fields
3. Click **"Update"**

### Deleting a Source
1. Click **🗑️ Delete** on any source
2. Confirm the deletion

---

## 🔐 Security

### Default Passcode
- Default passcode: `admin123`
- **⚠️ CHANGE THIS IMMEDIATELY** for production use!

### Changing the Passcode
**Method 1 - Via API (recommended):**
```python
import sys
sys.path.append('backend')
import source_manager

# Set new passcode
source_manager.update_passcode('your_new_secure_passcode')
```

**Method 2 - Direct Edit:**
Edit `backend/sources.json` and update the `passcode_hash` field (requires computing SHA-256 hash).

---

## 📋 Source Configuration

### Example `sources.json`
```json
{
  "sources": [
    {
      "id": "1",
      "name": "City Events Calendar",
      "url": "https://example.com/events",
      "type": "events",
      "enabled": true,
      "scraping_method": "auto",
      "custom_selectors": null
    },
    {
      "id": "2",
      "name": "Valdosta Main Street",
      "url": "https://www.valdostamainstreet.com/events-calendar",
      "type": "events",
      "enabled": true,
      "scraping_method": "calendar_table",
      "custom_selectors": {
        "calendar_table": "table",
        "event_cell": "td[data-date]",
        "event_link": "a[href*='/event/']",
        "date_attribute": "data-date"
      }
    }
  ],
  "settings": {
    "passcode_hash": "sha256_hash_here",
    "last_updated": "2025-01-10T00:00:00Z"
  }
}
```

### Custom Selectors (Advanced)

For calendar table format:
```json
"custom_selectors": {
  "calendar_table": "table.calendar",
  "event_cell": "td[data-date]",
  "event_link": "a",
  "date_attribute": "data-date"
}
```

For list format:
```json
"custom_selectors": {
  "item_container": "article.event",
  "title_selector": "h2",
  "link_selector": "a",
  "date_selector": ".event-date",
  "description_selector": "p"
}
```

---

## 🔧 API Endpoints

All endpoints require `passcode` parameter for authentication.

### Get All Sources
```
GET /api/sources?passcode=admin123
```

### Add Source
```
POST /api/sources?passcode=admin123
Body: {
  "name": "Source Name",
  "url": "https://example.com",
  "type": "events",
  "enabled": true,
  "scraping_method": "auto"
}
```

### Update Source
```
PUT /api/sources/{source_id}?passcode=admin123
Body: { "name": "New Name", ... }
```

### Delete Source
```
DELETE /api/sources/{source_id}?passcode=admin123
```

### Verify Passcode
```
POST /api/verify-passcode
Body: { "passcode": "admin123" }
```

---

## 🧪 Testing

### Test Backend
```bash
python3 -c "
import sys
sys.path.append('backend')
import source_manager
print('Sources:', len(source_manager.get_all_sources()))
print('Passcode works:', source_manager.verify_passcode('admin123'))
"
```

### Test Scraping a Source
```python
import sys
sys.path.append('backend')
from main import scrape_source
import source_manager

# Get first source
source = source_manager.get_all_sources()[0]

# Scrape it
results = scrape_source(source)
print(f"Found {len(results)} items from {source['name']}")
```

---

## 🐛 Troubleshooting

### "No events found"
- Check if sources are **enabled** in settings
- Verify the URLs are accessible
- Try changing scraping method to "AI-powered" (requires OpenAI API key)

### "Invalid passcode"
- Default passcode is `admin123`
- Check if you changed it in `sources.json`
- Clear browser localStorage: `localStorage.clear()`

### "Error scraping source"
- Check backend console for detailed error messages
- Website might be blocking requests (try AI-powered scraping)
- For calendar tables, you may need custom selectors

### Backend won't start
```bash
# Check Python dependencies
pip install -r backend/requirements.txt

# Check for syntax errors
python3 backend/main.py
```

---

## 📝 Migration from Old System

Your existing sources have been automatically migrated to `sources.json`:
- Visit Valdosta Events
- Valdosta Main Street Calendar
- Wanderlog Attractions
- Explore Georgia Guide
- TripAdvisor

The old hardcoded system is still in `main_backup.py` if you need to reference it.

---

## 🎯 Best Practices

1. **Test new sources** before enabling them in production
2. **Use descriptive names** for sources
3. **Disable unused sources** instead of deleting them
4. **Change the default passcode** immediately
5. **Keep `sources.json` backed up**
6. **Monitor scraping errors** in backend console
7. **Use AI scraping** for complex/dynamic websites

---

## 🚀 Next Steps

- Add more event sources!
- Customize scraping methods
- Change the default passcode
- Share sources with other users (export `sources.json`)

---

## 📞 Support

If you encounter issues:
1. Check backend console logs
2. Review this guide
3. Test with the default sources first
4. Try AI-powered scraping if auto-detect fails

---

**Enjoy your upgraded calendar app! 🎉**
