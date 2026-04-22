import pymysql
import numpy as np
import random
from datetime import datetime, timedelta

db_config = {
    'host':     'localhost',
    'user':     'root',
    'password': 'hello',
    'database': 'weather_system',
    'port':     3306
}

city_names = [
    "New Delhi", "Jaipur", "Chandigarh", "Shimla", "Dehradun",
    "Srinagar", "Lucknow", "Patna", "Kolkata", "Bhubaneswar",
    "Ranchi", "Raipur", "Guwahati", "Shillong", "Aizawl",
    "Kohima", "Imphal", "Agartala", "Itanagar", "Gangtok",
    "Mumbai", "Ahmedabad", "Panaji", "Bhopal", "Chennai",
    "Hyderabad", "Bengaluru", "Thiruvananthapuram", "Amaravati",
    "Port Blair", "Leh", "Daman", "Silvassa", "Kavaratti",
    "Puducherry"
]

cloudbursts = {
    ("New Delhi",  "2023-07-09"): 153.0,
    ("Mumbai",     "2024-07-15"): 215.4,
    ("Kolkata",    "2025-09-23"): 332.0,
    ("Chennai",    "2025-08-30"): 185.5,
    ("Guwahati",   "2025-06-10"): 120.2,
    ("Panaji",     "2023-07-20"): 145.0,
    ("Itanagar",   "2024-06-15"): 112.5,
    ("Port Blair", "2025-05-18"): 128.0,
}

hills         = {"Shimla", "Srinagar", "Gangtok", "Leh"}
heavy_monsoon = {"Mumbai", "Panaji", "Port Blair", "Silvassa", "Daman"}
ne_monsoon    = {"Chennai", "Puducherry"}

def get_connection():
    return pymysql.connect(
        **db_config,
        connect_timeout=300,
        read_timeout=300,
        write_timeout=300
    )

def build_city_rows(city, city_id):
    start_date  = datetime(2023, 1, 1)
    end_date    = datetime(2026, 3, 31)
    delta_days  = (end_date - start_date).days + 1
    now_ts      = datetime.now()
    rows        = []
    dirs        = ["N","NE","E","SE","S","SW","W","NW"]

    for i in range(delta_days):
        curr_date   = start_date + timedelta(days=i)
        date_str    = curr_date.strftime("%Y-%m-%d")
        month       = curr_date.month
        day_of_year = curr_date.timetuple().tm_yday

        # Temperature
        if city == "Leh":
            base = 2 + 18 * np.sin(2*np.pi*(day_of_year-150)/365)
        elif city in hills:
            base = 12 + 10 * np.sin(2*np.pi*(day_of_year-140)/365)
        else:
            base = 27 + 8  * np.sin(2*np.pi*(day_of_year-130)/365)

        temp     = round(base + random.uniform(-3, 3), 1)
        humidity = max(10, min(100, int(
            50 + 35 * np.sin(2*np.pi*(day_of_year-200)/365)
            + random.uniform(-10, 10)
        )))

        # Rainfall
        rainfall = 0.0
        if (city, date_str) in cloudbursts:
            rainfall = cloudbursts[(city, date_str)]
        elif city in hills and temp < 0 and month in [4,5,6]:
            rainfall = 0.0
        elif 6 <= month <= 9 and city not in ne_monsoon and city != "Leh":
            if random.random() < 0.4:
                scale    = 65 if city in heavy_monsoon else 15
                rainfall = round(random.expovariate(1/scale), 1)
        elif 10 <= month <= 12 and city in ne_monsoon:
            if random.random() < 0.35:
                rainfall = round(random.expovariate(1/40), 1)

        wind_deg   = random.randint(0, 360)
        wind_speed = round(random.uniform(5,15) + (
            random.uniform(5,10) if 6 <= month <= 9 else 0), 1)
        pressure   = (random.randint(780,820)
                      if city == "Leh"
                      else random.randint(980,1025))
        wind_str   = dirs[int((wind_deg+22.5)/45) % 8]

        rows.append((
            city_id, date_str, rainfall, temp,
            humidity, wind_speed, wind_str, pressure, now_ts
        ))
    return rows

def insert_city(city, city_id):
    rows    = build_city_rows(city, city_id)
    sql     = """
        INSERT IGNORE INTO weather_data
            (city_id, date, rainfall_mm, temperature_c,
             humidity_pct, wind_speed_kmh, wind_direction,
             pressure_hpa, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    # Insert in chunks of 100 rows — prevents timeout
    chunk_size = 10
    conn       = get_connection()
    try:
        cursor = conn.cursor()
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start:start+chunk_size]
            cursor.executemany(sql, chunk)
            conn.commit()
    finally:
        conn.close()
    return len(rows)

def generate_weather_data():
    # Get city map
    conn   = get_connection()
    cursor = conn.cursor()
    fmt    = ','.join(['%s'] * len(city_names))
    cursor.execute(
        f"SELECT id, name FROM cities WHERE name IN ({fmt})",
        tuple(city_names)
    )
    city_map = {name: cid for (cid, name) in cursor.fetchall()}
    conn.close()

    missing = set(city_names) - set(city_map.keys())
    if missing:
        print(f"⚠️  Missing cities: {missing}")
        return

    total = 0
    for city in city_names:
        try:
            n      = insert_city(city, city_map[city])
            total += n
            print(f"  ✓ {city} — {n} rows")
        except Exception as e:
            print(f"  ✗ {city} — ERROR: {e}")

    print("-" * 40)
    print(f"✅ Done. Total rows: {total}")

if __name__ == "__main__":
    generate_weather_data()