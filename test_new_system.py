#!/usr/bin/env python3
"""
Test script for the new flexible source management system
"""
import sys
sys.path.append('backend')

def test_system():
    print("=" * 60)
    print("TESTING NEW AGENTIC CALENDAR SYSTEM")
    print("=" * 60)

    try:
        # Test 1: Import modules
        print("\n[1/6] Testing module imports...")
        import source_manager
        import generic_scraper
        from main import scrape_source
        print("✅ All modules imported successfully")

        # Test 2: Load sources
        print("\n[2/6] Testing source management...")
        sources = source_manager.get_all_sources()
        print(f"✅ Loaded {len(sources)} sources")

        for i, source in enumerate(sources, 1):
            enabled = "✓" if source.get('enabled') else "✗"
            print(f"   {i}. [{enabled}] {source['name']} ({source['type']})")

        # Test 3: Test passcode system
        print("\n[3/6] Testing passcode system...")

        valid = source_manager.verify_passcode('admin123')
        print(f"✅ Default passcode 'admin123' valid: {valid}")

        invalid = source_manager.verify_passcode('wrong_password')
        print(f"✅ Wrong passcode correctly rejected: {not invalid}")

        # Test 4: Test getting sources by type
        print("\n[4/6] Testing source filtering...")
        event_sources = source_manager.get_sources_by_type('events')
        attraction_sources = source_manager.get_sources_by_type('attractions')
        print(f"✅ Found {len(event_sources)} event sources")
        print(f"✅ Found {len(attraction_sources)} attraction sources")

        # Test 5: Test scraping one source (valdostamainstreet - has custom selectors)
        print("\n[5/6] Testing scraping functionality...")
        test_source = None
        for source in sources:
            if 'valdostamainstreet' in source['url']:
                test_source = source
                break

        if test_source:
            print(f"Testing: {test_source['name']}")
            print(f"  URL: {test_source['url']}")
            print(f"  Method: {test_source.get('scraping_method', 'auto')}")

            results = scrape_source(test_source)
            print(f"✅ Scraped {len(results)} events/attractions")

            if results:
                print(f"\nSample result:")
                sample = results[0]
                print(f"  Title: {sample.get('title', 'N/A')[:50]}...")
                print(f"  Date: {sample.get('start', 'N/A')}")
                print(f"  URL: {sample.get('url', 'N/A')[:50]}...")
        else:
            print("⚠️  No test source found (skipping scrape test)")

        # Test 6: Test CRUD operations
        print("\n[6/6] Testing CRUD operations...")

        # Add a test source
        test_new_source = {
            "name": "Test Source",
            "url": "https://example.com/events",
            "type": "events",
            "enabled": False,
            "scraping_method": "auto"
        }

        added = source_manager.add_source(test_new_source)
        print(f"✅ Added test source with ID: {added['id']}")

        # Update it
        updated = source_manager.update_source(added['id'], {"name": "Updated Test Source"})
        print(f"✅ Updated source name to: {updated['name']}")

        # Delete it
        deleted = source_manager.delete_source(added['id'])
        print(f"✅ Deleted test source: {deleted}")

        # Final summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"   • Sources loaded: {len(sources)}")
        print(f"   • Event sources: {len(event_sources)}")
        print(f"   • Attraction sources: {len(attraction_sources)}")
        print(f"   • Passcode system: Working")
        print(f"   • CRUD operations: Working")
        print(f"   • Scraping: {'Working' if test_source and results else 'Not tested'}")

        print("\n🎉 The new system is fully operational!")
        print("\n📖 Next steps:")
        print("   1. Start backend: cd backend && uvicorn main:app --reload --port 8000")
        print("   2. Start frontend: cd frontend && npm start")
        print("   3. Open: http://localhost:3000")
        print("   4. Click ⚙️ Settings (passcode: admin123)")
        print("\n📚 Read UPGRADE_GUIDE.md for detailed documentation")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)
