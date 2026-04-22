# ============================================================
# routes/detection.py
# Cloud Burst Detection System — Detection Routes
# Cloudburst detection endpoints for React frontend
# ============================================================

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from modules.db import db
from modules.auth import require_permission
from sqlalchemy import text
from datetime import datetime

def rows_as_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def row_as_dict(cursor):
    cols = [d[0] for d in cursor.description]
    row  = cursor.fetchone()
    return dict(zip(cols, row)) if row else None

detection_bp = Blueprint("detection", __name__)


# ============================================================
# GET ALL CLOUDBURSTS
# GET /api/detection/cloudbursts
# Query params: city_id, status, limit
# ============================================================

@detection_bp.route("/cloudbursts", methods=["GET"])
@login_required
def get_cloudbursts():
    """
    Returns list of detected cloudbursts.
    Supports filtering by city and status.

    Query params:
        city_id: int   (optional — filter by city)
        status:  string (optional — Pending/Alerted/Dismissed)
        limit:   int   (default 50)
    """
    city_id = request.args.get("city_id", None, type=int)
    status  = request.args.get("status",  None)
    limit   = request.args.get("limit",   50, type=int)

    # Build dynamic WHERE clause
    filters = []
    params  = {"limit": limit}

    if city_id:
        filters.append("cb.city_id = :city_id")
        params["city_id"] = city_id

    if status:
        filters.append("cb.status = :status")
        params["status"] = status

    where = "WHERE " + " AND ".join(filters) if filters else ""

    query = text(f"""
        SELECT
            cb.id, cb.city_id, cb.date,
            cb.rainfall, cb.threshold,
            cb.delta, cb.percent_change,
            cb.status, cb.created_at,
            c.name  as city_name,
            c.state as state
        FROM cloudbursts cb
        JOIN cities c ON cb.city_id = c.id
        {where}
        ORDER BY cb.date DESC
        LIMIT :limit
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query, params).fetchall()

    cloudbursts = [
        {
            "id":             row[0],
            "city_id":        row[1],
            "date":           str(row[2]),
            "rainfall":       row[3],
            "threshold":      row[4],
            "delta":          row[5],
            "percent_change": row[6],
            "status":         row[7],
            "created_at":     str(row[8]),
            "city_name":      row[9],
            "state":          row[10]
        }
        for row in rows
    ]

    return jsonify({
        "cloudbursts": cloudbursts,
        "count":       len(cloudbursts)
    }), 200


# ============================================================
# GET ONE CLOUDBURST BY ID
# GET /api/detection/cloudbursts/<cloudburst_id>
# ============================================================

@detection_bp.route("/cloudbursts/<int:cloudburst_id>",
                    methods=["GET"])
@login_required
def get_cloudburst(cloudburst_id):
    """Returns full details of one cloudburst event."""
    query = text("""
        SELECT
            cb.id, cb.city_id, cb.date,
            cb.rainfall, cb.threshold,
            cb.delta, cb.percent_change,
            cb.status, cb.created_at,
            c.name  as city_name,
            c.state as state
        FROM cloudbursts cb
        JOIN cities c ON cb.city_id = c.id
        WHERE cb.id = :cloudburst_id
    """)

    with db.engine.connect() as conn:
        row = conn.execute(
            query, {"cloudburst_id": cloudburst_id}
        ).fetchone()

    if not row:
        return jsonify({"error": "Cloudburst not found"}), 404

    return jsonify({
        "id":             row[0],
        "city_id":        row[1],
        "date":           str(row[2]),
        "rainfall":       row[3],
        "threshold":      row[4],
        "delta":          row[5],
        "percent_change": row[6],
        "status":         row[7],
        "created_at":     str(row[8]),
        "city_name":      row[9],
        "state":          row[10]
    }), 200


# ============================================================
# TRIGGER EMAIL + SMS ALERT FOR CLOUDBURST
# POST /api/detection/cloudbursts/<cloudburst_id>/alert
# Admin only
# ============================================================

@detection_bp.route("/cloudbursts/<int:cloudburst_id>/alert",
                    methods=["POST"])
@login_required
@require_permission("trigger_alerts")
def trigger_alert(cloudburst_id):
    """
    Triggers Email + SMS alert for a confirmed cloudburst.
    Admin only — Step 4 of the alert flow.

    Returns:
        200 — { email, sms }
        404 — cloudburst not found
    """
    from modules.alerts import send_full_alert

    result = send_full_alert(
        cloudburst_id = cloudburst_id,
        triggered_by  = current_user.id
    )

    return jsonify({
        "message": "Alert triggered",
        "result":  result
    }), 200


# ============================================================
# DISMISS CLOUDBURST
# POST /api/detection/cloudbursts/<cloudburst_id>/dismiss
# Admin + Analyst
# ============================================================

@detection_bp.route("/cloudbursts/<int:cloudburst_id>/dismiss",
                    methods=["POST"])
@login_required
@require_permission("acknowledge_anomaly")
def dismiss_cloudburst(cloudburst_id):
    """
    Marks a cloudburst as Dismissed after review.
    Admin + Analyst only.
    """
    query = text("""
        UPDATE cloudbursts
        SET status     = 'Dismissed',
            updated_at = NOW()
        WHERE id = :cloudburst_id
    """)

    with db.engine.connect() as conn:
        result = conn.execute(
            query, {"cloudburst_id": cloudburst_id}
        )
        conn.commit()

    if result.rowcount == 0:
        return jsonify({"error": "Cloudburst not found"}), 404

    return jsonify({
        "message": "Cloudburst dismissed successfully"
    }), 200


# ============================================================
# GET CLOUDBURST STATISTICS
# GET /api/detection/stats
# Returns summary counts for dashboard
# ============================================================

@detection_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    """
    Returns cloudburst statistics for dashboard summary.

    Returns counts by status and recent 30 days trend.
    """
    # Count by status
    status_query = text("""
        SELECT status, COUNT(*) as count
        FROM cloudbursts
        GROUP BY status
    """)

    # Total this month
    month_query = text("""
        SELECT COUNT(*) as count
        FROM cloudbursts
        WHERE MONTH(date) = MONTH(NOW())
          AND YEAR(date)  = YEAR(NOW())
    """)

    # Total today
    today_query = text("""
        SELECT COUNT(*) as count
        FROM cloudbursts
        WHERE date = CURDATE()
    """)

    # Most affected cities (top 5)
    cities_query = text("""
        SELECT c.name, COUNT(*) as count
        FROM cloudbursts cb
        JOIN cities c ON cb.city_id = c.id
        GROUP BY cb.city_id, c.name
        ORDER BY count DESC
        LIMIT 5
    """)

    with db.engine.connect() as conn:
        status_rows = conn.execute(status_query).fetchall()
        month_count = conn.execute(month_query).scalar()
        today_count = conn.execute(today_query).scalar()
        city_rows   = conn.execute(cities_query).fetchall()

    status_counts = {row[0]: row[1] for row in status_rows}

    top_cities = [
        {"city": row[0], "count": row[1]}
        for row in city_rows
    ]

    return jsonify({
        "by_status": {
            "pending":   status_counts.get("Pending",   0),
            "alerted":   status_counts.get("Alerted",   0),
            "dismissed": status_counts.get("Dismissed", 0)
        },
        "this_month": month_count,
        "today":      today_count,
        "top_cities": top_cities
    }), 200


# ============================================================
# GET ALERT LOG
# GET /api/detection/alert-log
# Admin only
# ============================================================

@detection_bp.route("/alert-log", methods=["GET"])
@login_required
@require_permission("trigger_alerts")
def get_alert_log():
    """
    Returns history of all sent alerts.
    Admin only.
    """
    limit = request.args.get("limit", 50, type=int)

    query = text("""
        SELECT
            id, alert_type, city_name,
            alert_date, triggered_by,
            status, message, created_at
        FROM alert_log
        ORDER BY created_at DESC
        LIMIT :limit
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit}).fetchall()

    logs = [
        {
            "id":           row[0],
            "alert_type":   row[1],
            "city_name":    row[2],
            "alert_date":   str(row[3]),
            "triggered_by": row[4],
            "status":       row[5],
            "message":      row[6],
            "created_at":   str(row[7])
        }
        for row in rows
    ]

    return jsonify({
        "logs":  logs,
        "count": len(logs)
    }), 200