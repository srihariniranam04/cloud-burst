# routes/register.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pymysql

register_bp = Blueprint('register', __name__)

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "weather_system"),
        cursorclass=pymysql.cursors.DictCursor
    )

def send_welcome_email(to_email, username, plain_password):
    try:
        smtp_host     = os.getenv("SMTP_HOST")
        smtp_port     = int(os.getenv("SMTP_PORT", 587))
        smtp_user     = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email    = os.getenv("ALERT_FROM_EMAIL")

        subject = "Welcome to Cloud Burst — Account Created ☁️"
        body = f"""
Hi {username},

Your Cloud Burst account has been created successfully!

Login Credentials:
  Username : {username}
  Password : {plain_password}
  Role     : Viewer

You can log in at: http://localhost:5173/login
(Update this URL after deployment)

Please change your password after your first login.

— Cloud Burst Team
"""
        msg = MIMEMultipart()
        msg["From"]    = from_email
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())

        print(f"✅ Welcome email sent to {to_email}")
    except Exception as e:
        print(f"⚠️  Email failed: {e}")
        raise


@register_bp.route("/api/auth/register", methods=["POST"])
def register():
    data     = request.get_json()
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    phone    = data.get("phone", "").strip()
    password = data.get("password", "").strip()

    # Basic validation
    if not all([username, email, phone, password]):
        return jsonify({"error": "All fields are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check duplicate username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"error": "Username already taken"}), 409

        # Check duplicate email
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        # Insert new user — matches your exact schema
        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, phone, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, 1, NOW())
        """, (username, hashed, "viewer", email, phone))
        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    # Send welcome email (non-blocking failure)
    email_sent = True
    try:
        send_welcome_email(email, username, password)
    except Exception:
        email_sent = False

    return jsonify({
        "message": "Account created successfully!",
        "email_sent": email_sent
    }), 201