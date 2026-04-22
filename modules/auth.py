# ============================================================
# modules/auth.py
# Cloud Burst Detection System — Authentication + RBAC
# ============================================================

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from modules.db import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(100), unique=True, nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id":       self.id,
            "username": self.username,
            "email":    self.email,
            "role":     self.role
        }


# ============================================================
# RBAC Permission Definitions
# ============================================================

PERMISSIONS = {
    "view_dashboard":        ["admin", "analyst", "viewer"],
    "view_anomalies":        ["admin", "analyst", "viewer"],
    "download_pdf":          ["admin", "analyst", "viewer"],
    "generate_pdf":          ["admin", "analyst"],
    "acknowledge_anomaly":   ["admin", "analyst"],
    "add_notes":             ["admin", "analyst"],
    "trigger_alerts":        ["admin"],
    "configure_thresholds":  ["admin"],
    "manage_users":          ["admin"],
}


def has_permission(user, permission):
    """
    Check if a user has a specific permission.
    Usage: has_permission(current_user, "trigger_alerts")
    Returns: True or False
    """
    if not user or not user.is_authenticated:
        return False
    allowed_roles = PERMISSIONS.get(permission, [])
    return user.role in allowed_roles


def require_permission(permission):
    """
    Decorator to protect routes with RBAC.
    Usage: @require_permission("trigger_alerts")
    """
    from functools import wraps
    from flask import jsonify
    from flask_login import current_user

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    "error": "Login required"
                }), 401
            if not has_permission(current_user, permission):
                return jsonify({
                    "error": "You do not have permission to perform this action",
                    "required_permission": permission,
                    "your_role": current_user.role
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# User Loader for Flask-Login
# ============================================================

def init_login_manager(login_manager):
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))