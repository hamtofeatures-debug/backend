import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'agrosphere.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE user ADD COLUMN is_suspended BOOLEAN DEFAULT 0")
    conn.commit()
    print("Column 'is_suspended' added successfully.")
except sqlite3.OperationalError as e:
    print("Error (might already exist):", e)

conn.close()