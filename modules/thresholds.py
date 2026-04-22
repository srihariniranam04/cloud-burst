# ============================================================
# modules/thresholds.py
# Cloud Burst Detection System — Dynamic Threshold Calculation
# ============================================================

import pandas as pd
from datetime import datetime
from modules.db import db
from sqlalchemy import text


# ============================================================
# RECALCULATE THRESHOLDS FOR ALL CITIES + PARAMETERS
# Called every day after new data is fetched
# Source: weather_data table ONLY (last 3-5 years)
# Archive table is EXCLUDED
# ============================================================

def recalculate_all_thresholds():
    """
    Recalculates mean + std_dev for every city, parameter,
    and calendar month. Saves results to station_stats table.
    Called once daily after new data arrives.
    """
    print(f"[{datetime.now()}] Starting threshold recalculation...")

    parameters = [
        "rainfall", "temperature", "humidity",
        "wind_speed", "pressure"
    ]

    # Fetch all data from main table only
    query = text("""
        SELECT 
            city_id, 
            MONTH(date) as month,
            rainfall, 
            temperature, 
            humidity,
            wind_speed, 
            pressure
        FROM weather_data
        ORDER BY city_id, date
    """)

    with db.engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        columns = result.keys()

    if not rows:
        print("No data found in weather_data table.")
        return

    df = pd.DataFrame(rows, columns=columns)

    # Calculate mean + std_dev per city, per month, per parameter
    for param in parameters:
        if param not in df.columns:
            continue

        grouped = df.groupby(["city_id", "month"])[param].agg(
            mean_val="mean",
            std_val="std"
        ).reset_index()

        for _, row in grouped.iterrows():
            upsert = text("""
                INSERT INTO station_stats 
                    (city_id, parameter, month, mean_value, std_dev, updated_at)
                VALUES 
                    (:city_id, :parameter, :month, :mean_value, :std_dev, NOW())
                ON DUPLICATE KEY UPDATE
                    mean_value = VALUES(mean_value),
                    std_dev    = VALUES(std_dev),
                    updated_at = NOW()
            """)

            with db.engine.connect() as conn:
                conn.execute(upsert, {
                    "city_id":    int(row["city_id"]),
                    "parameter":  param,
                    "month":      int(row["month"]),
                    "mean_value": float(row["mean_val"]),
                    "std_dev":    float(row["std_val"]) if pd.notna(row["std_val"]) else 0.0
                })
                conn.commit()

    print(f"[{datetime.now()}] Threshold recalculation complete.")


# ============================================================
# GET THRESHOLD FOR ONE CITY + PARAMETER + MONTH
# Used during daily anomaly detection
# ============================================================

def get_threshold(city_id, parameter, month):
    """
    Fetches precomputed mean + std_dev for a specific
    city, parameter, and calendar month from station_stats.

    Returns:
        dict: { mean, std_dev, upper, lower }
        None: if no stats found
    """
    query = text("""
        SELECT mean_value, std_dev
        FROM station_stats
        WHERE city_id   = :city_id
          AND parameter = :parameter
          AND month     = :month
        LIMIT 1
    """)

    with db.engine.connect() as conn:
        result = conn.execute(query, {
            "city_id":   city_id,
            "parameter": parameter,
            "month":     month
        })
        row = result.fetchone()

    if not row:
        return None

    mean    = float(row[0])
    std_dev = float(row[1])

    return {
        "mean":    mean,
        "std_dev": std_dev,
        "upper":   mean + 2 * std_dev,
        "lower":   mean - 2 * std_dev
    }


# ============================================================
# GET DYNAMIC CLOUDBURST THRESHOLD FOR ONE CITY + MONTH
# Cloudburst threshold = mean + 2*std_dev for rainfall
# ============================================================

def get_cloudburst_threshold(city_id, month):
    """
    Returns the dynamic cloudburst threshold for rainfall.
    Cloudburst threshold = mean + 2 * std_dev of rainfall.

    Returns:
        float: threshold value
        None:  if no stats found
    """
    threshold = get_threshold(city_id, "rainfall", month)
    if not threshold:
        return None
    return threshold["upper"]


# ============================================================
# CHECK ANOMALY STATUS FOR A SINGLE VALUE
# Returns "HIGH", "LOW", or "normal"
# ============================================================

def check_anomaly(city_id, parameter, month, value):
    """
    Checks if a given value is anomalous (2σ rule).

    Returns:
        "HIGH"   — value > mean + 2*std_dev
        "LOW"    — value < mean - 2*std_dev
        "normal" — within range
        None     — if no threshold data exists
    """
    threshold = get_threshold(city_id, parameter, month)
    if not threshold:
        return None

    if value > threshold["upper"]:
        return "HIGH"
    elif value < threshold["lower"]:
        return "LOW"
    else:
        return "normal"