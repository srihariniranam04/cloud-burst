# ============================================================
# modules/db.py
# Cloud Burst Detection System — Database Instance
# ============================================================

from flask_sqlalchemy import SQLAlchemy
import pymysql
from config import Config

# Single shared db instance used across all modules
db = SQLAlchemy()


def get_db_connection():
    """
    Returns a raw pymysql connection.
    Used by routes that need direct cursor access.
    Always call conn.close() after use.
    """
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"[DB ERROR] Connection failed: {e}")
        return None