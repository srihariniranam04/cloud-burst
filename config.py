# ============================================================
# Cloud Burst Detection System — Configuration
# ============================================================

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    # --- Database ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "weather_system")

    # SQLAlchemy connection string
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Visual Crossing API ---
    VISUAL_CROSSING_API_KEY = os.getenv("VISUAL_CROSSING_API_KEY", "")
    VISUAL_CROSSING_BASE_URL = (
        "https://weather.visualcrossing.com/VisualCrossingWebServices"
        "/rest/services/timeline"
    )

    # --- Email (Gmail SMTP) ---
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    ALERT_FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "")
    ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL", "")

    # --- Twilio SMS ---
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
    TWILIO_TO_NUMBER = os.getenv("TWILIO_TO_NUMBER", "")

    # --- Directories ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPORTS_DIR = os.path.join(BASE_DIR, os.getenv("REPORTS_DIR", "reports"))
    DATA_DIR = os.path.join(BASE_DIR, os.getenv("DATA_DIR", "data"))
    HISTORICAL_CSV = os.path.join(BASE_DIR, os.getenv("HISTORICAL_CSV", "data/historical_raw.csv"))

    # --- Detection Thresholds ---
    SPIKE_DELTA_THRESHOLD = 50        # mm — minimum delta for spike
    SPIKE_PERCENT_THRESHOLD = 100     # % — minimum percent change for spike
    ANOMALY_STD_MULTIPLIER = 2        # 2σ standard deviation multiplier

    # --- Data Retention ---
    ARCHIVE_AFTER_YEARS = 5           # move data older than 5 years to archive

    # --- Auto Refresh ---
    AUTO_REFRESH_SECONDS = 3600       # 1 hour

    # --- Cities ---
    CITIES = [
        "New Delhi", "Jaipur", "Chandigarh", "Shimla", "Dehradun",
        "Srinagar", "Lucknow", "Patna", "Kolkata", "Bhubaneswar",
        "Ranchi", "Raipur", "Guwahati", "Shillong", "Aizawl",
        "Kohima", "Imphal", "Agartala", "Itanagar", "Gangtok",
        "Mumbai", "Ahmedabad", "Panaji", "Bhopal", "Chennai",
        "Hyderabad", "Bengaluru", "Thiruvananthapuram", "Amaravati",
        "Port Blair", "Leh", "Daman", "Silvassa", "Kavaratti",
        "Puducherry"
    ]

    # --- Weather Parameters ---
    DETECTION_PARAMETERS = [
        "rainfall", "temperature", "humidity",
        "wind_speed", "pressure"
    ]
    DISPLAY_PARAMETERS = [
        "rainfall", "temperature", "humidity",
        "wind_speed", "pressure", "wind_direction"
    ]