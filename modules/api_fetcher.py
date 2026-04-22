# modules/api_fetcher.py
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from modules.db import get_db_connection

load_dotenv()


def get_city_map():
    """Returns {city_name: city_id} from DB."""
    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM cities ORDER BY id")
        rows = cursor.fetchall()
        return {row["name"]: row["id"] for row in rows}
    except Exception as e:
        print(f"[ERROR] get_city_map: {e}")
        return {}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def fetch_city_weather(city_name, date_str):
    """Fetch one city's weather from Visual Crossing for date_str."""
    api_key = os.getenv("VISUAL_CROSSING_API_KEY", "")
    if not api_key or api_key == "YOUR_ACTUAL_KEY_HERE":
        print("  [ERROR] VISUAL_CROSSING_API_KEY not set in .env")
        return None

    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices"
        f"/rest/services/timeline/{city_name},{date_str}/{date_str}"
        f"?unitGroup=metric"
        f"&elements=datetime,temp,humidity,precip,windspeed,winddir,pressure"
        f"&include=days"
        f"&key={api_key}"
        f"&contentType=json"
    )

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"  [ERROR] {city_name} — HTTP {response.status_code}")
            return None

        data = response.json()
        days = data.get("days", [])
        if not days:
            print(f"  [ERROR] {city_name} — No day data returned")
            return None

        day = days[0]
        return {
            "temperature_c":  day.get("temp",      None),
            "humidity_pct":   day.get("humidity",  None),
            "rainfall_mm":    day.get("precip",    0) or 0,
            "wind_speed_kmh": day.get("windspeed", None),
            "wind_direction": str(day.get("winddir", "")) if day.get("winddir") is not None else None,
            "pressure_hpa":   day.get("pressure",  None),
        }

    except requests.exceptions.Timeout:
        print(f"  [ERROR] {city_name} — Request timed out")
        return None
    except Exception as e:
        print(f"  [ERROR] {city_name} — {e}")
        return None


def save_weather(city_id, date_str, weather):
    """Insert one row into weather_data. Skips if duplicate."""
    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT IGNORE INTO weather_data
                (city_id, date, temperature_c, humidity_pct,
                 rainfall_mm, wind_speed_kmh, wind_direction,
                 pressure_hpa, source, created_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, 'visualcrossing', NOW())
        """, (
            city_id,
            date_str,
            weather["temperature_c"],
            weather["humidity_pct"],
            weather["rainfall_mm"],
            weather["wind_speed_kmh"],
            weather["wind_direction"],
            weather["pressure_hpa"],
        ))
        conn.commit()
    except Exception as e:
        print(f"  [ERROR] save_weather city_id={city_id}: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def fetch_all_cities_today():
    """Fetch today's weather for all 35 cities and save to DB."""
    today    = datetime.now().date()
    date_str = today.strftime("%Y-%m-%d")

    print(f"Fetching weather for all cities — {date_str}")

    city_map = get_city_map()
    if not city_map:
        print("[ERROR] No cities found in DB.")
        return {"success": 0, "failed": 0}

    success = 0
    failed  = 0

    for city_name, city_id in city_map.items():
        api_name = f"{city_name},India"
        print(f"  Fetching {city_name}...")
        weather = fetch_city_weather(api_name, date_str)

        if weather:
            save_weather(city_id, date_str, weather)
            print(f"  ✓ {city_name}")
            success += 1
        else:
            print(f"  ✗ {city_name} failed")
            failed += 1

    print(f"Fetch complete — Success: {success}, Failed: {failed}")
    return {"success": success, "failed": failed}