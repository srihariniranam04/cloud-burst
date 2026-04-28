# app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from modules.db import db
from routes.auth      import auth_bp
from routes.weather   import weather_bp
from routes.detection import detection_bp
from routes.anomalies import anomalies_bp
from routes.reports   import reports_bp
from routes.register import register_bp
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)

    # auth, weather, detection get their prefix here
    app.register_blueprint(auth_bp,      url_prefix="/api/auth")
    app.register_blueprint(weather_bp,   url_prefix="/api/weather")
    app.register_blueprint(detection_bp, url_prefix="/api/detection")
    app.register_blueprint(register_bp)
    # anomalies and reports have /api/ hardcoded inside their route files
    app.register_blueprint(anomalies_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        return {"status": "Cloud Burst Detection API is running"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)