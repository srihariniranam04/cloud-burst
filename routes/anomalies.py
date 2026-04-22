# routes/anomalies.py
from flask import Blueprint, jsonify, request
from modules.db import get_db_connection

anomalies_bp = Blueprint("anomalies", __name__)


@anomalies_bp.route("/api/anomalies/recent", methods=["GET"])
def recent_anomalies():
    conn   = None
    cursor = None
    limit  = request.args.get("limit", 100, type=int)
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                a.id,
                c.name          AS city_name,
                c.state,
                a.detected_date,
                a.parameter,
                a.observed_value,
                a.mean_value,
                a.std_dev,
                a.deviation_type,
                a.status,
                a.notes
            FROM anomalies a
            JOIN cities c ON c.id = a.city_id
            ORDER BY a.detected_date DESC, a.id DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        for r in rows:
            r["detected_date"] = str(r["detected_date"])
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@anomalies_bp.route("/api/anomalies/count", methods=["GET"])
def anomaly_count():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*)                                    AS total,
                SUM(deviation_type = 'HIGH')                AS high_count,
                SUM(deviation_type = 'LOW')                 AS low_count,
                SUM(status = 'open')                        AS open_count,
                SUM(status = 'acknowledged')                AS acknowledged_count
            FROM anomalies
        """)
        row = cursor.fetchone()
        return jsonify(row or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@anomalies_bp.route("/api/anomalies/by-city", methods=["GET"])
def anomalies_by_city():
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                c.name  AS city_name,
                c.state,
                COUNT(*) AS anomaly_count,
                SUM(a.deviation_type = 'HIGH') AS high_count,
                SUM(a.deviation_type = 'LOW')  AS low_count
            FROM anomalies a
            JOIN cities c ON c.id = a.city_id
            GROUP BY a.city_id, c.name, c.state
            ORDER BY anomaly_count DESC
            LIMIT 20
        """)
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@anomalies_bp.route("/api/anomalies/<int:anomaly_id>/acknowledge", methods=["POST"])
def acknowledge_anomaly(anomaly_id):
    conn   = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "DB connection failed"}), 500
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE anomalies
            SET status = 'acknowledged',
                acknowledged_at = NOW()
            WHERE id = %s
        """, (anomaly_id,))
        conn.commit()
        return jsonify({"success": True, "id": anomaly_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()