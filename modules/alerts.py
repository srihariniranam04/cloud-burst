# ============================================================
# modules/alerts.py
# Cloud Burst Detection System — Email + SMS Alerts
# Triggered ONLY by Admin after manual review
# Every alert is logged to alert_log table
# ============================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from modules.db import db
from config import Config
from sqlalchemy import text


# ============================================================
# SEND EMAIL ALERT
# Uses Gmail SMTP + App Password
# ============================================================

def send_email_alert(city_name, date, rainfall, threshold, triggered_by):
    """
    Sends a cloudburst email alert via Gmail SMTP to ALL registered users.
    """
    subject = f"🌧️ CLOUDBURST ALERT — {city_name} on {date}"

    body = f"""
CLOUDBURST ALERT
================

City         : {city_name}
Date         : {date}
Rainfall     : {rainfall} mm
Threshold    : {threshold} mm
Triggered By : Admin (ID: {triggered_by})
Time         : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This is an automated alert from the Cloud Burst 
Identification and Weather Anomaly Detection System.

Immediate action may be required.
Please review the dashboard for full details.
"""

    # Fetch all active users with an email
    email_query = text("""
        SELECT id, username, email
        FROM users
        WHERE is_active = 1
        AND email IS NOT NULL
        AND email != ''
    """)

    try:
        with db.engine.connect() as conn:
            users = conn.execute(email_query).fetchall()

        results = []
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)

            for user in users:
                user_id    = user[0]
                user_name  = user[1]
                user_email = user[2]

                try:
                    msg = MIMEMultipart()
                    msg["From"]    = Config.ALERT_FROM_EMAIL
                    msg["To"]      = user_email
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body, "plain"))

                    server.sendmail(
                        Config.ALERT_FROM_EMAIL,
                        user_email,
                        msg.as_string()
                    )

                    _log_alert(
                        alert_type   = "Email",
                        city_name    = city_name,
                        date         = date,
                        triggered_by = triggered_by,
                        status       = "Sent",
                        message      = f"Email sent to {user_name} ({user_email})"
                    )

                    print(f"  [EMAIL] ✓ Sent to {user_name} ({user_email})")
                    results.append({"user": user_name, "success": True})

                except Exception as e:
                    _log_alert(
                        alert_type   = "Email",
                        city_name    = city_name,
                        date         = date,
                        triggered_by = triggered_by,
                        status       = "Failed",
                        message      = f"Failed for {user_name} ({user_email}): {str(e)}"
                    )
                    print(f"  [EMAIL] ✗ Failed for {user_name}: {str(e)}")
                    results.append({"user": user_name, "success": False})

        return {"success": True, "message": f"Email attempted for {len(users)} users", "results": results}

    except smtplib.SMTPAuthenticationError:
        error = "Gmail authentication failed. Check App Password in .env"
        _log_alert(
            alert_type   = "Email",
            city_name    = city_name,
            date         = date,
            triggered_by = triggered_by,
            status       = "Failed",
            message      = error
        )
        print(f"  [EMAIL] ✗ {error}")
        return {"success": False, "message": error}

    except Exception as e:
        error = str(e)
        _log_alert(
            alert_type   = "Email",
            city_name    = city_name,
            date         = date,
            triggered_by = triggered_by,
            status       = "Failed",
            message      = error
        )
        print(f"  [EMAIL] ✗ {error}")
        return {"success": False, "message": error}
# ============================================================
# SEND SMS ALERT
# Uses Twilio Python SDK
# ============================================================

def send_sms_alert(city_name, date, rainfall, threshold, triggered_by):
    """
    Sends a cloudburst SMS alert via Twilio to ALL registered users.
    """
    sms_body = (
        f"CLOUDBURST ALERT\n"
        f"City: {city_name}\n"
        f"Date: {date}\n"
        f"Rainfall: {rainfall}mm "
        f"(Threshold: {threshold}mm)\n"
        f"Time: {datetime.now().strftime('%H:%M %d-%m-%Y')}"
    )

    # Fetch all active users with a phone number
    phone_query = text("""
        SELECT id, username, phone 
        FROM users 
        WHERE is_active = 1 
        AND phone IS NOT NULL 
        AND phone != ''
    """)

    with db.engine.connect() as conn:
        users = conn.execute(phone_query).fetchall()

    if not users:
        return {"success": False, "message": "No users with phone numbers found"}

    try:
        from twilio.rest import Client
        client = Client(
            Config.TWILIO_ACCOUNT_SID,
            Config.TWILIO_AUTH_TOKEN
        )

        results = []
        for user in users:
            user_id       = user[0]
            username      = user[1]
            phone_number  = user[2]

            try:
                message = client.messages.create(
                    body  = sms_body,
                    from_ = Config.TWILIO_FROM_NUMBER,
                    to    = phone_number
                )

                _log_alert(
                    alert_type   = "SMS",
                    city_name    = city_name,
                    date         = date,
                    triggered_by = triggered_by,
                    status       = "Sent",
                    message      = f"SMS sent to {username} ({phone_number}) SID: {message.sid}"
                )

                print(f"  [SMS] ✓ Sent to {username} ({phone_number})")
                results.append({"user": username, "success": True})

            except Exception as e:
                _log_alert(
                    alert_type   = "SMS",
                    city_name    = city_name,
                    date         = date,
                    triggered_by = triggered_by,
                    status       = "Failed",
                    message      = f"Failed for {username} ({phone_number}): {str(e)}"
                )
                print(f"  [SMS] ✗ Failed for {username}: {str(e)}")
                results.append({"user": username, "success": False})

        success_count = sum(1 for r in results if r["success"])
        return {
            "success": success_count > 0,
            "message": f"SMS sent to {success_count}/{len(users)} users",
            "details": results
        }

    except Exception as e:
        error = str(e)
        print(f"  [SMS] ✗ Twilio client error: {error}")
        return {"success": False, "message": error}
# ============================================================
# SEND BOTH EMAIL + SMS TOGETHER
# Main function called from Admin dashboard
# ============================================================

def send_full_alert(cloudburst_id, triggered_by):
    """
    Sends both Email + SMS alerts for a confirmed cloudburst.
    Called only by Admin after manual review.

    Args:
        cloudburst_id: int — ID from cloudbursts table
        triggered_by:  int — user_id of Admin

    Returns:
        dict: { email, sms }
    """
    # Fetch cloudburst details
    query = text("""
        SELECT 
            cb.id, cb.city_id, cb.date,
            cb.rainfall, cb.threshold,
            c.name as city_name
        FROM cloudbursts cb
        JOIN cities c ON cb.city_id = c.id
        WHERE cb.id = :cloudburst_id
    """)

    with db.engine.connect() as conn:
        row = conn.execute(
            query, {"cloudburst_id": cloudburst_id}
        ).fetchone()

    if not row:
        return {
            "email": {"success": False, "message": "Cloudburst not found"},
            "sms":   {"success": False, "message": "Cloudburst not found"}
        }

    city_name = row[5]
    date      = row[2]
    rainfall  = row[3]
    threshold = row[4]

    print(f"[{datetime.now()}] Sending alerts for "
          f"{city_name} on {date}...")

    # Send both
    email_result = send_email_alert(
        city_name, date, rainfall, threshold, triggered_by
    )
    sms_result = send_sms_alert(
        city_name, date, rainfall, threshold, triggered_by
    )

    # Update cloudburst status to Alerted
    update_query = text("""
        UPDATE cloudbursts
        SET status = 'Alerted', updated_at = NOW()
        WHERE id = :cloudburst_id
    """)

    with db.engine.connect() as conn:
        conn.execute(update_query, {"cloudburst_id": cloudburst_id})
        conn.commit()

    return {
        "email": email_result,
        "sms":   sms_result
    }


# ============================================================
# LOG ALERT TO alert_log TABLE
# ============================================================

def _log_alert(alert_type, city_name, date,
               triggered_by, status, message):
    """Saves every alert attempt to alert_log table."""
    query = text("""
        INSERT INTO alert_log
            (alert_type, city_name, alert_date,
             triggered_by, status, message, created_at)
        VALUES
            (:alert_type, :city_name, :alert_date,
             :triggered_by, :status, :message, NOW())
    """)

    try:
        with db.engine.connect() as conn:
            conn.execute(query, {
                "alert_type":   alert_type,
                "city_name":    city_name,
                "alert_date":   date,
                "triggered_by": triggered_by,
                "status":       status,
                "message":      message
            })
            conn.commit()
    except Exception as e:
        print(f"  [LOG ERROR] Could not save alert log: {str(e)}")