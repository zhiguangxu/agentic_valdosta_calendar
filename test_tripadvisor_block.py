#!/usr/bin/env python3
"""
Test script to verify TripAdvisor is completely blocked
"""
import sys
sys.path.append('backend')

def test_tripadvisor_blocking():
    print("=" * 60)
    print("TESTING TRIPADVISOR BLOCKING")
    print("=" * 60)

    try:
        import source_manager

        # Test 1: Verify TripAdvisor is removed from sources
        print("\n[1/4] Checking sources.json...")
        sources = source_manager.get_all_sources()
        tripadvisor_found = any('tripadvisor' in s['url'].lower() for s in sources)

        if tripadvisor_found:
            print("❌ FAILED: TripAdvisor still exists in sources.json")
            return False
        else:
            print("✅ PASSED: TripAdvisor not in sources.json")
            print(f"   Current sources: {len(sources)}")
            for s in sources:
                print(f"   - {s['name']}")

        # Test 2: Try to add TripAdvisor URL
        print("\n[2/4] Testing backend validation (add)...")
        test_tripadvisor_source = {
            "name": "Test TripAdvisor",
            "url": "https://www.tripadvisor.com/test",
            "type": "attractions",
            "enabled": True
        }

        try:
            source_manager.add_source(test_tripadvisor_source)
            print("❌ FAILED: Backend allowed TripAdvisor to be added")
            return False
        except ValueError as e:
            if "TripAdvisor" in str(e) and "not supported" in str(e):
                print("✅ PASSED: Backend correctly blocked TripAdvisor")
                print(f"   Error message: {str(e)}")
            else:
                print(f"❌ FAILED: Wrong error message: {e}")
                return False

        # Test 3: Try different TripAdvisor variations
        print("\n[3/4] Testing various TripAdvisor URL patterns...")
        test_urls = [
            "https://www.tripadvisor.com/Attractions",
            "https://tripadvisor.com/test",
            "https://www.TripAdvisor.com/test",  # Different case
            "https://www.tripadvisor.co.uk/test",  # Different TLD
        ]

        all_blocked = True
        for test_url in test_urls:
            try:
                source_manager.add_source({
                    "name": "Test",
                    "url": test_url,
                    "type": "attractions"
                })
                print(f"❌ FAILED: {test_url} was not blocked")
                all_blocked = False
            except ValueError:
                print(f"✅ Blocked: {test_url}")

        if not all_blocked:
            return False

        # Test 4: Try to update existing source to TripAdvisor
        print("\n[4/4] Testing backend validation (update)...")
        # Get any existing source
        existing_sources = source_manager.get_all_sources()
        if existing_sources:
            test_source_id = existing_sources[0]['id']
            try:
                source_manager.update_source(test_source_id, {
                    "url": "https://www.tripadvisor.com/test"
                })
                print("❌ FAILED: Backend allowed updating to TripAdvisor URL")
                return False
            except ValueError as e:
                if "TripAdvisor" in str(e):
                    print("✅ PASSED: Backend blocked update to TripAdvisor URL")
                else:
                    print(f"❌ FAILED: Wrong error: {e}")
                    return False
        else:
            print("⚠️  SKIPPED: No sources to test update")

        # Summary
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nTripAdvisor is completely blocked:")
        print("  ✓ Removed from sources.json")
        print("  ✓ Backend rejects adding TripAdvisor URLs")
        print("  ✓ Backend rejects updating to TripAdvisor URLs")
        print("  ✓ All URL variations blocked")
        print("\nUsers will see this error message:")
        print('  "TripAdvisor is not supported due to scraping restrictions.')
        print('   Please use alternative attraction sources."')

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tripadvisor_blocking()
    sys.exit(0 if success else 1)
