# test_alerts.py
import sys
sys.path.insert(0, ".")

from app import create_app
from modules.alerts import send_email_alert, send_sms_alert

app = create_app()

with app.app_context():
    # Test Email
    print("Testing Email...")
    email_result = send_email_alert(
        city_name    = "Hyderabad",
        date         = "2026-04-29",
        rainfall     = 120.5,
        threshold    = 100.0,
        triggered_by = 4
    )
    print("Email Result:", email_result)

    # Test SMS
    print("\nTesting SMS...")
    sms_result = send_sms_alert(
        city_name    = "Hyderabad",
        date         = "2026-04-29",
        rainfall     = 120.5,
        threshold    = 100.0,
        triggered_by = 4
    )
    print("SMS Result:", sms_result)