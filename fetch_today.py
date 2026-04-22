# fetch_today.py
# Run daily to fetch today's weather for all 35 cities
# Usage: python fetch_today.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from modules.api_fetcher import fetch_all_cities_today
from modules.detection import run_detection

print("=" * 55)
print("STEP 1 — Fetching today's weather for all 35 cities")
print("=" * 55)
result = fetch_all_cities_today()
print(f"\n✅ Fetch done — Success: {result['success']}, Failed: {result['failed']}")

print("\n" + "=" * 55)
print("STEP 2 — Running anomaly detection")
print("=" * 55)
run_detection()
print("✅ Detection complete")

print("\n" + "=" * 55)
print("ALL DONE — Refresh your dashboard")
print("=" * 55)