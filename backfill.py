# backfill.py
# Run once to fetch missing dates from April 15 to April 28
# Usage: python backfill.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from datetime import date, timedelta
from modules.api_fetcher import get_city_map, fetch_city_weather, save_weather
from modules.detection import run_detection

# ── Date range to backfill ───────────────────────────────
START_DATE = date(2026, 4, 15)
END_DATE   = date(2026, 4, 28)
# ─────────────────────────────────────────────────────────

def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

city_map = get_city_map()
if not city_map:
    print("[ERROR] No cities found in DB.")
    sys.exit(1)

total_success = 0
total_failed  = 0

for single_date in daterange(START_DATE, END_DATE):
    date_str = single_date.strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"Fetching {date_str} for all cities...")
    print(f"{'='*50}")

    for city_name, city_id in city_map.items():
        api_name = f"{city_name},India"
        weather  = fetch_city_weather(api_name, date_str)
        if weather:
            save_weather(city_id, date_str, weather)
            print(f"  ✓ {city_name}")
            total_success += 1
        else:
            print(f"  ✗ {city_name} failed")
            total_failed += 1

print(f"\n{'='*50}")
print(f"BACKFILL COMPLETE")
print(f"  Success : {total_success}")
print(f"  Failed  : {total_failed}")
print(f"{'='*50}")

print("\nRunning anomaly detection on new data...")
run_detection()
print("Done!")