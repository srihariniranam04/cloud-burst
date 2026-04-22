# modules/detection.py
# Run standalone:  python modules/detection.py
# Or import:       from modules.detection import run_detection

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.db import get_db_connection

PARAMETERS = [
    ("rainfall_mm",    "rainfall"),
    ("temperature_c",  "temperature"),
    ("humidity_pct",   "humidity"),
    ("wind_speed_kmh", "wind_speed"),
    ("pressure_hpa",   "pressure"),
]

THRESHOLD_SIGMA = 2.0   # flag anything beyond 2 standard deviations


def run_detection(city_id=None):
    conn   = None
    cursor = None
    inserted = 0
    skipped  = 0
    errors   = 0

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        if city_id:
            cursor.execute("SELECT id, name FROM cities WHERE id = %s", (city_id,))
        else:
            cursor.execute("SELECT id, name FROM cities ORDER BY id")
        cities = cursor.fetchall()

        print(f"Processing {len(cities)} cities ...")

        for city in cities:
            cid   = city["id"]
            cname = city["name"]

            for col, param_label in PARAMETERS:
                cursor.execute(f"""
                    SELECT date, {col} AS val
                    FROM   weather_data
                    WHERE  city_id = %s
                      AND  {col} IS NOT NULL
                    ORDER  BY date
                """, (cid,))
                rows = cursor.fetchall()

                if len(rows) < 30:
                    continue

                values   = [float(r["val"]) for r in rows]
                n        = len(values)
                mean     = sum(values) / n
                variance = sum((v - mean) ** 2 for v in values) / n
                std_dev  = variance ** 0.5

                if std_dev == 0:
                    continue

                for r in rows:
                    val  = float(r["val"])
                    diff = abs(val - mean)

                    if diff <= THRESHOLD_SIGMA * std_dev:
                        continue

                    dev_type = "HIGH" if val > mean else "LOW"
                    det_date = r["date"]

                    # Skip duplicates
                    cursor.execute("""
                        SELECT id FROM anomalies
                        WHERE  city_id      = %s
                          AND  detected_date = %s
                          AND  parameter     = %s
                    """, (cid, det_date, param_label))

                    if cursor.fetchone():
                        skipped += 1
                        continue

                    try:
                        cursor.execute("""
                            INSERT INTO anomalies
                              (city_id, detected_date, parameter,
                               observed_value, mean_value, std_dev,
                               deviation_type, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
                        """, (
                            cid,
                            det_date,
                            param_label,
                            round(val,     2),
                            round(mean,    2),
                            round(std_dev, 2),
                            dev_type
                        ))
                        conn.commit()
                        inserted += 1
                    except Exception as ie:
                        errors += 1
                        print(f"  INSERT error [{cname}/{param_label}/{det_date}]: {ie}")

            print(f"  ✓ {cname}")

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    print(f"\n=== Detection complete ===")
    print(f"  Inserted : {inserted}")
    print(f"  Skipped  : {skipped}  (duplicates)")
    print(f"  Errors   : {errors}")
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    run_detection()