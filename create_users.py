# create_users.py
from werkzeug.security import generate_password_hash
import pymysql

users = [
    ('admin',   'admin123',   'admin',   'admin@weather.com'),
    ('analyst', 'analyst123', 'analyst', 'analyst@weather.com'),
    ('viewer',  'viewer123',  'viewer',  'viewer@weather.com'),
]

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='hello',
    database='weather_system'
)
cursor = conn.cursor()

# Delete old bcrypt-hashed users first
cursor.execute("DELETE FROM users WHERE username IN ('admin', 'analyst', 'viewer')")
print("🗑️  Deleted old users")

for username, plain_password, role, email in users:
    hashed = generate_password_hash(plain_password)
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, email, is_active, created_at)
        VALUES (%s, %s, %s, %s, 1, NOW())
    """, (username, hashed, role, email))
    print(f"✅ Created user: {username} / {plain_password} ({role})")

conn.commit()
conn.close()
print("\n✅ All users re-created with correct password hashing.")