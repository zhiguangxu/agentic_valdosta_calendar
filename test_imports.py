#!/usr/bin/env python3
"""
Quick test to verify imports work correctly
"""

print("Testing backend imports...")

try:
    # Test importing as a package (how uvicorn imports it)
    from backend import main
    from backend import source_manager
    from backend import generic_scraper

    print("✅ All modules imported successfully!")

    # Test basic functionality
    sources = source_manager.get_all_sources()
    print(f"✅ Loaded {len(sources)} sources from sources.json")

    print(f"✅ FastAPI app created: {main.app is not None}")

    print("\n🎉 Backend is ready to start!")
    print("\nTo start the backend, run:")
    print("  uv run uvicorn backend.main:app --reload --port 8000")

except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    print("\nIf you see import errors, make sure:")
    print("1. You're running from the project root directory")
    print("2. backend/__init__.py exists")
    print("3. All files are in backend/: main.py, source_manager.py, generic_scraper.py, sources.json")
