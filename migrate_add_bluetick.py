# migrate_add_bluetick.py
import sqlite3, os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'agrosphere.db')
conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE user ADD COLUMN blue_tick BOOLEAN DEFAULT 0")
    conn.commit()
    print("blue_tick column added.")
except Exception as e:
    print(e)
conn.close()