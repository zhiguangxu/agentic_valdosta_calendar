#!/usr/bin/env python3
"""Debug: See what AI extracts from Ceramics page"""

import sys
import os
sys.path.insert(0, '/Users/zhiguangxu/Documents/workspace/AgenticAI/agents/agentic_valdosta_calendar')

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime, timedelta
import json

# Check API key
if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not set!")
    sys.exit(1)

client = OpenAI()

url = "https://turnercenter.org/ceramics_education/"

print(f"Fetching: {url}")
resp = requests.get(url)
soup = BeautifulSoup(resp.text, "html.parser")

# Remove script, style, nav, footer
for element in soup(["script", "style", "nav", "footer", "header"]):
    element.decompose()

content = str(soup.body)[:30000] if soup.body else str(soup)[:30000]

today = datetime.now()
six_months = today + timedelta(days=180)

# Use the actual Stage 2 classes prompt
from backend.generic_scraper import _generate_stage2_classes_prompt

prompt = _generate_stage2_classes_prompt("CERAMICS & POTTERY", content, "", today, six_months)

print("\nCalling OpenAI API...")
print("="*60)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1
)

raw_response = response.choices[0].message.content.strip()

print("\nRAW AI RESPONSE:")
print("="*60)
print(raw_response)
print("="*60)

# Try to parse as JSON
if raw_response.startswith("```json"):
    raw_response = raw_response[7:]
if raw_response.startswith("```"):
    raw_response = raw_response[3:]
if raw_response.endswith("```"):
    raw_response = raw_response[:-3]
raw_response = raw_response.strip()

try:
    data = json.loads(raw_response)
    print("\nPARSED JSON:")
    print("="*60)
    print(f"Category: {data.get('category')}")
    print(f"Number of classes: {len(data.get('classes', []))}")
    print()

    for i, cls in enumerate(data.get('classes', []), 1):
        print(f"{i}. {cls.get('title')}")
        print(f"   Dates: {cls.get('dates')}")
        print(f"   Time: {cls.get('time')}")
        print(f"   Recurring: {cls.get('recurring_pattern')}")
        print()
except json.JSONDecodeError as e:
    print(f"\nJSON PARSE ERROR: {e}")
