# Verification Guide: Testing the Implementation

## Quick Verification Steps

### 1. Test Recurring Event Detection (Valdosta City "First Friday")

**Enable Valdosta City source:**
1. Go to Settings page
2. Find "Valdosta City" source
3. Ensure it's **enabled** (toggle ON)
4. Scraping method should be: **ai_twostage**

**Test the scraping:**
1. Go to **Events** tab
2. Click **"Refresh Data"** button
3. Watch the console logs (if accessible) or wait for results

**Expected Results:**
- You should see "First Friday" events appearing on:
  - March 7, 2026 (first Friday of March)
  - April 4, 2026 (first Friday of April)
  - May 1, 2026 (first Friday of May)
  - June 5, 2026 (first Friday of June)
  - July 3, 2026 (first Friday of July)

**What to look for:**
```
Console logs should show:
[RECURRING] Detected 'First Friday' pattern: First Friday [Event Name]
  [RECURRING] Generated: First Friday [Event Name] on 2026-03-07
  [RECURRING] Generated: First Friday [Event Name] on 2026-04-04
  ...
```

### 2. Test Category Isolation

**Test 1: Events don't affect Classes**
1. Go to **Events** tab, click "Refresh Data"
2. Note the events that appear
3. Go to **Classes** tab, click "Refresh Data"
4. Verify classes appear correctly (Turner Center classes)
5. The classes should NOT be mixed with events

**Test 2: Make a change to events sources**
1. In Settings, disable "Visit Valdosta" (events source)
2. Refresh Events tab → fewer events
3. Refresh Classes tab → classes unchanged ✅

**Expected:**
- ✅ Events tab shows only events
- ✅ Classes tab shows only classes
- ✅ Changes to event sources don't affect classes

### 3. Test Deduplication

**Test Events Deduplication:**
1. Enable multiple event sources: "Visit Valdosta" + "Valdosta City"
2. Click "Refresh Data" on Events tab
3. Look for events that might appear on both sources
4. Verify you see each event only ONCE (deduplicated)

**Console logs to check:**
```
[DEDUP] New event: [Event Name] on 2026-XX-XX
[DEDUP] Duplicate found:
  Existing: [Event Name]
  Current: [Similar Event Name]
  → Keeping existing (longer title)
```

### 4. Verify Category-Specific Behavior

**Events:**
- Event titles should NOT have year prefixes like "2026"
- Event titles should NOT have "Annual" prefix
- All events should be in the FUTURE (no past events)

**Classes:**
- Class titles SHOULD keep ordinals like "2nd Week", "Week 3"
- Classes from the last 30 days might appear (ongoing series)
- Instructor names should be visible if available

**Meetings:**
- Meeting titles SHOULD keep year prefixes (e.g., "2026 Annual Meeting")
- Exact meeting names preserved
- All meetings should be in the FUTURE

## Console Logs to Monitor

### Successful Recurring Event Detection:
```
[Two-Stage] Starting two-stage scraping for https://www.valdostacity.com/calendar
[Two-Stage] Stage 1: Extracting events from listing page (using AI)
  AI extracted X items from [URL]
  Adding: First Friday [Event Name] on 2026-02-07
    Recurring: first friday of each month
[Two-Stage] Stage 2: Scraping X external event pages
[Two-Stage] After expanding recurring events: Y events
  [RECURRING] Detected 'First Friday' pattern: First Friday [Event Name]
    [RECURRING] Generated: First Friday [Event Name] on 2026-03-07
    [RECURRING] Generated: First Friday [Event Name] on 2026-04-04
    ...
```

### Successful Category Isolation:
```
[EVENTS] Total items before deduplication: X
[EVENTS] Total items after deduplication: Y

[CLASSES] Total items before deduplication: X
[CLASSES] Total items after deduplication: Y
```

### Successful Deduplication:
```
[DEDUP] Duplicate found:
  Existing: 2026 Annual Spring Festival
  Current: Spring Festival
  Key: 2026-03-15_spring festival
  → Keeping existing (longer title)
```

## Troubleshooting

### Issue: "First Friday" appears only once
**Cause:** Recurring pattern not detected
**Fix:** Check console for `[RECURRING] Detected` message. If missing:
  - Verify `recurring_pattern` field is being extracted in Stage 1
  - Ensure pattern contains "first friday" (case insensitive)

### Issue: Events and Classes are mixed
**Cause:** Source type mismatch
**Fix:** Check `sources.json` - ensure each source has correct `type`:
  - Events sources: `"type": "events"`
  - Classes sources: `"type": "classes"`

### Issue: Too many duplicates appearing
**Cause:** Deduplication not working
**Fix:** Check console for `[DEDUP]` messages. If missing:
  - Verify category is routing to correct deduplication function
  - Check that normalized keys are matching

### Issue: No events appearing
**Cause:** Sources disabled or scraping failing
**Fix:**
  1. Check Settings - ensure sources are enabled
  2. Check console for scraping errors
  3. Verify OpenAI API key is set
  4. Try refreshing the page

## Success Criteria

✅ **Recurring Events Working:**
- First Friday event appears 5+ times in calendar
- Each occurrence is on the first Friday of the month
- Console shows "[RECURRING] Generated" messages

✅ **Category Isolation Working:**
- Events tab shows only events
- Classes tab shows only classes
- Disabling an event source doesn't affect classes

✅ **Deduplication Working:**
- No duplicate events with same date and similar titles
- Console shows "Duplicate found" and "Keeping existing/current" messages

✅ **Category-Specific Processing:**
- Event titles clean (no "2026", "Annual" prefixes)
- Class titles keep ordinals ("2nd Week")
- Meeting titles keep year prefixes

## Backend Server

If you need to restart the backend:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

## Need Help?

If something isn't working:
1. Check the console logs (browser dev tools + terminal where backend runs)
2. Look for error messages with `[Two-Stage]`, `[RECURRING]`, or `[DEDUP]` prefixes
3. Verify your sources in Settings have correct configurations
4. Ensure OpenAI API key is set: `export OPENAI_API_KEY='your-key'`
