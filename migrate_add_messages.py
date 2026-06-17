# migrate_add_messages.py
import sqlite3, os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'instance', 'agrosphere.db')
conn = sqlite3.connect(db_path)
try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES user(id),
            receiver_id INTEGER NOT NULL REFERENCES user(id),
            content TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("Message table created.")
except Exception as e:
    print(e)
conn.close()