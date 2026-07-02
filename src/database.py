import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stocks.db")


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                ticker  TEXT PRIMARY KEY,
                name    TEXT NOT NULL,
                sector  TEXT
            )
        """)
        self.conn.commit()

    def insert_stock(self, ticker, name, sector):
        self.conn.execute(
            "INSERT OR IGNORE INTO stocks (ticker, name, sector) VALUES (?, ?, ?)",
            (ticker, name, sector)
        )
        self.conn.commit()

    def get_all_stocks(self):
        cursor = self.conn.execute("SELECT ticker, name, sector FROM stocks ORDER BY name")
        return cursor.fetchall()

    def search_stocks(self, query):
        cursor = self.conn.execute(
            "SELECT ticker, name, sector FROM stocks WHERE name LIKE ? OR ticker LIKE ? ORDER BY name",
            (f"%{query}%", f"%{query}%")
        )
        return cursor.fetchall()

    def close(self):
        self.conn.close()
