# routes/reports.py
from flask import Blueprint, request, jsonify, send_file, session
from modules.db import get_db_connection
from modules.pdf_generator import generate_pdf
from datetime import datetime, date
import os

reports_bp = Blueprint('reports', __name__)


def get_session_user():
    """Return current user from Flask session or None."""
    if 'user_id' not in session:
        return None
    return {
        'id':       session['user_id'],
        'username': session['username'],
        'role':     session['role'],
    }


def require_login():
    user = get_session_user()
    if not user:
        return None, (jsonify({'error': 'Authentication required'}), 401)
    return user, None


def require_generate():
    user, err = require_login()
    if err:
        return None, err
    if user['role'].lower() not in ('admin', 'analyst'):
        return None, (jsonify({'error': 'Permission denied. Admin or Analyst role required.'}), 403)
    return user, None


# ─────────────────────────────────────────────────────────
# GET /api/reports
# List all generated PDF reports
# ─────────────────────────────────────────────────────────
@reports_bp.route('/api/reports', methods=['GET'])
def list_reports():
    user, err = require_login()
    if err:
        return err

    city_id  = request.args.get('city_id',  type=int)
    page     = max(1, request.args.get('page',     default=1,  type=int))
    per_page = request.args.get('per_page', default=20, type=int)
    if per_page < 1 or per_page > 100:
        per_page = 20
    offset = (page - 1) * per_page

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        conditions = []
        params     = []
        if city_id:
            conditions.append("r.city_id = %s")
            params.append(city_id)
        where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"SELECT COUNT(*) AS total FROM pdf_reports r {where_sql}", params)
        total = cursor.fetchone()['total']

        cursor.execute(f"""
            SELECT
                r.id, r.city_id,
                c.name      AS city_name,
                r.report_type, r.start_date, r.end_date,
                r.file_path, r.generated_by,
                u.username  AS generated_by_name,
                r.created_at
            FROM pdf_reports r
            JOIN cities c ON c.id = r.city_id
            LEFT JOIN users u ON u.id = r.generated_by
            {where_sql}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        rows = cursor.fetchall()

        for row in rows:
            for key in ('start_date', 'end_date', 'created_at'):
                if isinstance(row.get(key), (datetime, date)):
                    row[key] = row[key].isoformat()

        return jsonify({
            'page':        page,
            'per_page':    per_page,
            'total':       total,
            'total_pages': (total + per_page - 1) // per_page,
            'reports':     rows
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─────────────────────────────────────────────────────────
# POST /api/reports/generate
# ─────────────────────────────────────────────────────────
@reports_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    user, err = require_generate()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    city_id     = data.get('city_id')
    report_type = data.get('report_type', 'custom')
    start_date  = data.get('start_date')
    end_date    = data.get('end_date')

    if not city_id:
        return jsonify({'error': 'city_id is required'}), 400
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    if report_type not in ('daily', 'weekly', 'monthly', 'custom'):
        return jsonify({'error': 'report_type must be daily/weekly/monthly/custom'}), 400
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date,   '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Dates must be YYYY-MM-DD'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must be before end_date'}), 400

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Verify city
        cursor.execute("SELECT id, name, state FROM cities WHERE id = %s", (city_id,))
        city = cursor.fetchone()
        if not city:
            return jsonify({'error': 'City not found'}), 404

        # Weather data
        cursor.execute("""
            SELECT * FROM weather_data
            WHERE city_id = %s AND date BETWEEN %s AND %s
            ORDER BY date ASC
        """, (city_id, start_date, end_date))
        weather_rows = cursor.fetchall()

        # Anomalies
        cursor.execute("""
            SELECT * FROM anomalies
            WHERE city_id = %s AND detected_date BETWEEN %s AND %s
            ORDER BY detected_date ASC
        """, (city_id, start_date, end_date))
        anomaly_rows = cursor.fetchall()

        # Cloudbursts
        cursor.execute("""
            SELECT * FROM cloudbursts
            WHERE city_id = %s AND date BETWEEN %s AND %s
            ORDER BY date ASC
        """, (city_id, start_date, end_date))
        cloudburst_rows = cursor.fetchall()

        # Serialise dates
        for row in list(weather_rows) + list(anomaly_rows) + list(cloudburst_rows):
            for key, val in row.items():
                if isinstance(val, (datetime, date)):
                    row[key] = val.isoformat()

        # Build payload
        report_payload = {
            'city_name':    city['name'],
            'state_name':   city.get('state', 'India'),
            'report_type':  report_type,
            'start_date':   start_date,
            'end_date':     end_date,
            'generated_by': user['username'],
            'weather_data': weather_rows,
            'anomalies':    anomaly_rows,
            'cloudbursts':  cloudburst_rows,
            'summary': {
                'total_days':        len(weather_rows),
                'total_anomalies':   len(anomaly_rows),
                'total_cloudbursts': len(cloudburst_rows),
                'avg_rainfall':      round(
                    sum(float(r.get('rainfall_mm') or 0) for r in weather_rows)
                    / max(1, len(weather_rows)), 2),
                'avg_temperature':   round(
                    sum(float(r.get('temperature_c') or 0) for r in weather_rows)
                    / max(1, len(weather_rows)), 2),
                'max_rainfall':      max(
                    (float(r.get('rainfall_mm') or 0) for r in weather_rows),
                    default=0),
            }
        }

        # Generate PDF
        result    = generate_pdf(report_payload)
        file_path = result.get('file_path')
        if not file_path:
            return jsonify({'error': 'PDF generation failed'}), 500

        # Save record
        cursor.execute("""
            INSERT INTO pdf_reports
                (city_id, report_type, start_date, end_date,
                 file_path, generated_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (city_id, report_type, start_date, end_date,
              file_path, user['id']))
        conn.commit()
        report_id = cursor.lastrowid

        return jsonify({
            'message':     'Report generated successfully',
            'report_id':   report_id,
            'file_path':   file_path,
            'city':        city['name'],
            'report_type': report_type,
            'start_date':  start_date,
            'end_date':    end_date,
            'summary':     report_payload['summary']
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─────────────────────────────────────────────────────────
# GET /api/reports/<id>/download
# ─────────────────────────────────────────────────────────
@reports_bp.route('/api/reports/<int:report_id>/download', methods=['GET'])
def download_report(report_id):
    user, err = require_login()
    if err:
        return err

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.name AS city_name
            FROM pdf_reports r
            JOIN cities c ON c.id = r.city_id
            WHERE r.id = %s
        """, (report_id,))
        report = cursor.fetchone()

        if not report:
            return jsonify({'error': 'Report not found'}), 404

        file_path = report['file_path']
        if not os.path.exists(file_path):
            return jsonify({'error': 'PDF file not found on disk'}), 404

        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─────────────────────────────────────────────────────────
# DELETE /api/reports/<id>
# Admin only
# ─────────────────────────────────────────────────────────
@reports_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    user, err = require_login()
    if err:
        return err
    if user['role'].lower() != 'admin':
        return jsonify({'error': 'Admin role required'}), 403

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, file_path FROM pdf_reports WHERE id = %s", (report_id,)
        )
        report = cursor.fetchone()
        if not report:
            return jsonify({'error': 'Report not found'}), 404

        file_path = report['file_path']
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        cursor.execute("DELETE FROM pdf_reports WHERE id = %s", (report_id,))
        conn.commit()

        return jsonify({'message': 'Report deleted', 'report_id': report_id}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()