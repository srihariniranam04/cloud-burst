import pymysql

conn = pymysql.connect(
    host='localhost', user='root',
    password='hello', database='weather_system', port=3306
)
cursor = conn.cursor()
cursor.execute("SET GLOBAL wait_timeout = 600")
cursor.execute("SET GLOBAL interactive_timeout = 600")
cursor.execute("SET GLOBAL net_read_timeout = 600")
cursor.execute("SET GLOBAL net_write_timeout = 600")
conn.commit()
conn.close()
print("✅ Timeouts updated successfully")