# 🚀 Quick Start Guide

## Fixed: Import Error

The `ModuleNotFoundError: No module named 'source_manager'` has been **FIXED**! ✅

### What Was Changed:
1. Added `backend/__init__.py` to make it a proper Python package
2. Updated imports in `main.py` to use relative imports
3. Backend now runs from project root (not from backend directory)

---

## ✅ How to Start the Application

### Step 1: Verify Setup
From the **project root directory**, run:
```bash
python3 test_imports.py
```

You should see:
```
✅ All modules imported successfully!
✅ Loaded 5 sources from sources.json
✅ FastAPI app created: True
🎉 Backend is ready to start!
```

### Step 2: Start Backend
**Terminal 1 - Backend:**
```bash
# Make sure you're in the PROJECT ROOT directory
uv run uvicorn backend.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 3: Start Frontend
**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### Step 4: Access the App
1. Open: http://localhost:3000
2. Click the **⚙️ Settings** button (top-right)
3. Enter passcode: **admin123**
4. Manage your event sources!

---

## ⚠️ Important Notes

### Always Run from Project Root
**CORRECT** ✅
```bash
# You should be here:
/path/to/agentic_valdosta_calendar/
uv run uvicorn backend.main:app --reload --port 8000
```

**WRONG** ❌
```bash
# Don't run from here:
/path/to/agentic_valdosta_calendar/backend/
uvicorn main:app --reload --port 8000
```

### If You Don't Use `uv`
Use standard Python instead:
```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

---

## 🐛 Troubleshooting

### Import Errors
If you still see import errors:
1. Check you're in the **project root** directory (not backend/)
2. Verify `backend/__init__.py` exists
3. Run `python3 test_imports.py` to diagnose

### Port Already in Use
If port 8000 is already in use:
```bash
# Use a different port
uv run uvicorn backend.main:app --reload --port 8001
```

### Module Not Found (uvicorn)
If uvicorn isn't installed:
```bash
pip install uvicorn fastapi
# OR
uv pip install uvicorn fastapi
```

---

## 📁 Project Structure

```
agentic_valdosta_calendar/          ← YOU ARE HERE (run commands from here)
├── backend/
│   ├── __init__.py                 ← NEW! Makes it a package
│   ├── main.py                     ← Updated imports
│   ├── source_manager.py           ← NEW!
│   ├── generic_scraper.py          ← NEW!
│   └── sources.json                ← NEW!
├── frontend/
│   └── src/
│       ├── App.js                  ← Updated
│       └── Settings.js             ← NEW!
├── test_imports.py                 ← NEW! Test script
├── START_HERE.md                   ← This file
└── UPGRADE_GUIDE.md                ← Full documentation
```

---

## ✅ Verification Checklist

Before starting, verify:
- [ ] You're in the project root directory
- [ ] `backend/__init__.py` exists
- [ ] `python3 test_imports.py` passes
- [ ] Port 8000 is available

---

## 🎯 Next Steps

1. **Start the app** using the commands above
2. **Test the settings page** - add a new source
3. **Change the default passcode** from `admin123`
4. **Read** `UPGRADE_GUIDE.md` for full documentation

---

## 📞 Need Help?

Run the test script first:
```bash
python3 test_imports.py
```

If tests pass but backend won't start, check:
- Are you in the project root?
- Is port 8000 available?
- Do you have all dependencies installed?

---

**Ready to go! 🚀 Run the commands above and enjoy your upgraded calendar app!**
