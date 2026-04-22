# ============================================================
# modules/data_loader.py
# Cloud Burst Detection System — CSV to MySQL Loader
# Loads 5 years historical data from Visual Crossing CSV
# Run ONCE on Day 1 to populate weather_data table
# ============================================================

import pandas as pd
from datetime import datetime
from modules.db import db
from sqlalchemy import text


# ============================================================
# EXPECTED CSV COLUMNS FROM VISUAL CROSSING
# When downloading CSV from Visual Crossing, these are
# the column names it provides
# ============================================================

COLUMN_MAP = {
    "datetime":       "date",
    "temp":           "temperature",
    "tempmax":        "temp_max",
    "tempmin":        "temp_min",
    "humidity":       "humidity",
    "precip":         "rainfall",
    "windspeed":      "wind_speed",
    "winddir":        "wind_direction",
    "pressure":       "pressure"
}


# ============================================================
# LOAD CSV FOR ONE CITY INTO weather_data TABLE
# ============================================================

def load_city_csv(csv_path, city_id, city_name):
    """
    Loads historical CSV data for one city into weather_data.

    Args:
        csv_path:  path to CSV file
        city_id:   int — city ID from cities table
        city_name: string — for logging only

    Returns:
        dict: { inserted, skipped, errors }
    """
    print(f"[{datetime.now()}] Loading CSV for {city_name}...")

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"  [ERROR] File not found: {csv_path}")
        return {"inserted": 0, "skipped": 0, "errors": 1}
    except Exception as e:
        print(f"  [ERROR] Could not read CSV: {str(e)}")
        return {"inserted": 0, "skipped": 0, "errors": 1}

    # Rename columns to match our DB schema
    df = df.rename(columns=COLUMN_MAP)

    # Keep only columns we need
    required_cols = [
        "date", "temperature", "temp_max", "temp_min",
        "humidity", "rainfall", "wind_speed",
        "wind_direction", "pressure"
    ]

    # Add missing columns as None
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df = df[required_cols]

    # Clean data
    df["date"]          = pd.to_datetime(df["date"]).dt.date
    df["rainfall"]      = pd.to_numeric(df["rainfall"],      errors="coerce").fillna(0)
    df["temperature"]   = pd.to_numeric(df["temperature"],   errors="coerce")
    df["temp_max"]      = pd.to_numeric(df["temp_max"],      errors="coerce")
    df["temp_min"]      = pd.to_numeric(df["temp_min"],      errors="coerce")
    df["humidity"]      = pd.to_numeric(df["humidity"],      errors="coerce")
    df["wind_speed"]    = pd.to_numeric(df["wind_speed"],    errors="coerce")
    df["wind_direction"]= pd.to_numeric(df["wind_direction"],errors="coerce")
    df["pressure"]      = pd.to_numeric(df["pressure"],      errors="coerce")

    inserted = 0
    skipped  = 0
    errors   = 0

    insert_query = text("""
        INSERT IGNORE INTO weather_data
            (city_id, date, temperature, temp_max, temp_min,
             humidity, rainfall, wind_speed, wind_direction,
             pressure, created_at)
        VALUES
            (:city_id, :date, :temperature, :temp_max, :temp_min,
             :humidity, :rainfall, :wind_speed, :wind_direction,
             :pressure, NOW())
    """)

    with db.engine.connect() as conn:
        for _, row in df.iterrows():
            try:
                result = conn.execute(insert_query, {
                    "city_id":        city_id,
                    "date":           row["date"],
                    "temperature":    _safe(row["temperature"]),
                    "temp_max":       _safe(row["temp_max"]),
                    "temp_min":       _safe(row["temp_min"]),
                    "humidity":       _safe(row["humidity"]),
                    "rainfall":       _safe(row["rainfall"]),
                    "wind_speed":     _safe(row["wind_speed"]),
                    "wind_direction": _safe(row["wind_direction"]),
                    "pressure":       _safe(row["pressure"])
                })
                if result.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  [ROW ERROR] {row['date']} — {str(e)}")
                errors += 1

        conn.commit()

    print(f"  {city_name} — Inserted: {inserted}, "
          f"Skipped: {skipped}, Errors: {errors}")

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


# ============================================================
# LOAD SINGLE COMBINED CSV FOR ALL CITIES
# Visual Crossing bulk download has a 'name' column
# with city name — we use that to split by city
# ============================================================

def load_combined_csv(csv_path):
    """
    Loads a single CSV that contains data for multiple cities.
    Visual Crossing bulk downloads include a 'name' column
    identifying each city.

    Args:
        csv_path: path to combined CSV file

    Returns:
        dict: { total_inserted, total_skipped, total_errors }
    """
    print(f"[{datetime.now()}] Loading combined CSV: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"  [ERROR] File not found: {csv_path}")
        return {"total_inserted": 0, "total_skipped": 0, "total_errors": 1}

    if "name" not in df.columns:
        print("  [ERROR] CSV does not have a 'name' column.")
        print("  Use load_city_csv() for single city CSVs instead.")
        return {"total_inserted": 0, "total_skipped": 0, "total_errors": 1}

    # Get city map from DB
    city_map = get_city_map()

    total_inserted = 0
    total_skipped  = 0
    total_errors   = 0

    # Split by city name and load each
    for city_name, group in df.groupby("name"):
        # Try to match city name to DB
        city_id = city_map.get(city_name)
        if not city_id:
            # Try partial match
            city_id = _fuzzy_city_match(city_name, city_map)

        if not city_id:
            print(f"  [SKIP] City not found in DB: {city_name}")
            total_skipped += len(group)
            continue

        # Save group to temp CSV and load
        import tempfile, os
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv",
            delete=False, newline=""
        ) as tmp:
            group.to_csv(tmp, index=False)
            tmp_path = tmp.name

        result = load_city_csv(tmp_path, city_id, city_name)
        os.unlink(tmp_path)

        total_inserted += result["inserted"]
        total_skipped  += result["skipped"]
        total_errors   += result["errors"]

    print(f"[{datetime.now()}] Combined CSV load complete.")
    print(f"  Total Inserted : {total_inserted}")
    print(f"  Total Skipped  : {total_skipped}")
    print(f"  Total Errors   : {total_errors}")

    return {
        "total_inserted": total_inserted,
        "total_skipped":  total_skipped,
        "total_errors":   total_errors
    }


# ============================================================
# HELPER — GET CITY MAP FROM DATABASE
# ============================================================

def get_city_map():
    """Returns dict of { city_name: city_id } from DB."""
    query = text("SELECT id, name FROM cities")
    with db.engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return {row[1]: row[0] for row in rows}


# ============================================================
# HELPER — FUZZY CITY NAME MATCHING
# Handles cases like "New Delhi" vs "Delhi"
# ============================================================

def _fuzzy_city_match(city_name, city_map):
    """
    Tries partial name matching if exact match fails.
    Returns city_id or None.
    """
    city_name_lower = city_name.lower().strip()
    for db_city, city_id in city_map.items():
        if (city_name_lower in db_city.lower() or
                db_city.lower() in city_name_lower):
            return city_id
    return None


# ============================================================
# HELPER — SAFE FLOAT CONVERSION
# Returns None for NaN values
# ============================================================

def _safe(value):
    """Converts NaN to None for MySQL compatibility."""
    import math
    if value is None:
        return None
    try:
        if math.isnan(float(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None