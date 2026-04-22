# routes/weather.py
from flask import Blueprint, jsonify, request
from modules.db import get_db_connection

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/summary", methods=["GET"])
def weather_summary():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ROUND(AVG(wd.rainfall_mm), 2)    AS avg_rainfall,
                ROUND(AVG(wd.temperature_c), 2)  AS avg_temperature,
                ROUND(AVG(wd.humidity_pct), 2)   AS avg_humidity,
                ROUND(AVG(wd.wind_speed_kmh), 2) AS avg_wind_speed,
                ROUND(AVG(wd.pressure_hpa), 2)   AS avg_pressure,
                MAX(wd.date)                      AS latest_date
            FROM weather_data wd
            WHERE wd.date = (SELECT MAX(date) FROM weather_data)
        """)
        row = cursor.fetchone()
        if row and row.get("latest_date"):
            row["latest_date"] = str(row["latest_date"])
        return jsonify(row or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/cities", methods=["GET"])
def get_cities():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("SELECT id, name AS city_name, state FROM cities ORDER BY name")
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/rainfall-chart", methods=["GET"])
def rainfall_chart():
    conn   = None
    cursor = None
    days   = request.args.get("days", 30, type=int)
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                wd.date,
                ROUND(AVG(wd.rainfall_mm), 2) AS avg_rainfall,
                ROUND(MAX(wd.rainfall_mm), 2) AS max_rainfall
            FROM weather_data wd
            WHERE wd.date >= CURDATE() - INTERVAL %s DAY
            GROUP BY wd.date
            ORDER BY wd.date ASC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/temperature-chart", methods=["GET"])
def temperature_chart():
    conn   = None
    cursor = None
    days   = request.args.get("days", 30, type=int)
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                wd.date,
                ROUND(AVG(wd.temperature_c), 2) AS avg_temp,
                ROUND(MAX(wd.temperature_c), 2) AS max_temp,
                ROUND(MIN(wd.temperature_c), 2) AS min_temp
            FROM weather_data wd
            WHERE wd.date >= CURDATE() - INTERVAL %s DAY
            GROUP BY wd.date
            ORDER BY wd.date ASC
        """, (days,))
        rows = cursor.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/heatmap", methods=["GET"])
def heatmap():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                c.name AS city_name,
                c.state,
                ROUND(wd.rainfall_mm, 2)    AS rainfall_mm,
                ROUND(wd.temperature_c, 2)  AS temperature_c,
                ROUND(wd.humidity_pct, 2)   AS humidity_pct,
                ROUND(wd.wind_speed_kmh, 2) AS wind_speed_kmh,
                ROUND(wd.pressure_hpa, 2)   AS pressure_hpa,
                wd.date
            FROM weather_data wd
            JOIN cities c ON c.id = wd.city_id
            WHERE wd.date = (SELECT MAX(date) FROM weather_data)
            ORDER BY wd.rainfall_mm DESC
            LIMIT 12
        """)
        rows = cursor.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/city/<int:city_id>", methods=["GET"])
def city_weather(city_id):
    conn   = None
    cursor = None
    days   = request.args.get("days", 30, type=int)
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                wd.date,
                wd.rainfall_mm,
                wd.temperature_c,
                wd.humidity_pct,
                wd.wind_speed_kmh,
                wd.wind_direction,
                wd.pressure_hpa,
                c.name AS city_name,
                c.state
            FROM weather_data wd
            JOIN cities c ON c.id = wd.city_id
            WHERE wd.city_id = %s
              AND wd.date >= CURDATE() - INTERVAL %s DAY
            ORDER BY wd.date DESC
        """, (city_id, days))
        rows = cursor.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@weather_bp.route("/latest", methods=["GET"])
def latest_weather():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                c.name AS city_name,
                c.state,
                wd.date,
                wd.rainfall_mm,
                wd.temperature_c,
                wd.humidity_pct,
                wd.wind_speed_kmh,
                wd.wind_direction,
                wd.pressure_hpa
            FROM weather_data wd
            JOIN cities c ON c.id = wd.city_id
            INNER JOIN (
                SELECT city_id, MAX(date) AS max_date
                FROM weather_data
                GROUP BY city_id
            ) latest ON wd.city_id = latest.city_id
                     AND wd.date   = latest.max_date
            ORDER BY c.name AS city_name
        """)
        rows = cursor.fetchall()
        for r in rows:
            r["date"] = str(r["date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()