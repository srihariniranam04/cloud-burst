# routes/auth.py
from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash
from modules.db import get_db_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        session["user_id"]  = user["id"]
        session["username"] = user["username"]
        session["role"]     = user["role"]

        return jsonify({
            "message":  "Login successful",
            "username": user["username"],
            "role":     user["role"]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "user_id":  session["user_id"],
        "username": session["username"],
        "role":     session["role"]
    }), 200