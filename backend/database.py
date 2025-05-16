import sqlite3
import json
from datetime import datetime

DB_NAME = "crypto.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                data TEXT
            )
        """)
        conn.commit()

def save_data(data):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO market_data (timestamp, data) VALUES (?, ?)",
                       (datetime.utcnow().isoformat(), json.dumps(data)))
        conn.commit()

def get_latest_data():
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, data FROM market_data ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return {"timestamp": row[0], "data": json.loads(row[1])}
        return {"timestamp": None, "data": []}
