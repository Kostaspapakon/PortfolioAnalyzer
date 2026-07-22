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
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker       TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                target_price REAL,
                notes        TEXT,
                added_date   TEXT NOT NULL
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

    def get_sectors(self, tickers):
        placeholders = ",".join("?" * len(tickers))
        cursor = self.conn.execute(
            f"SELECT ticker, sector FROM stocks WHERE ticker IN ({placeholders})",
            tickers
        )
        return dict(cursor.fetchall())

    def get_sector(self, ticker):
        cursor = self.conn.execute("SELECT sector FROM stocks WHERE ticker = ?", (ticker,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_stocks_by_sector(self, sector, exclude_ticker, limit=3):
        cursor = self.conn.execute(
            "SELECT ticker, name FROM stocks WHERE sector = ? AND ticker != ? LIMIT ?",
            (sector, exclude_ticker, limit)
        )
        return cursor.fetchall()

    def add_to_watchlist(self, ticker, name, target_price=None, notes=None):
        from datetime import date
        self.conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, name, target_price, notes, added_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (ticker, name, target_price, notes, str(date.today())),
        )
        self.conn.commit()

    def remove_from_watchlist(self, ticker):
        self.conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        self.conn.commit()

    def get_watchlist(self):
        cursor = self.conn.execute(
            "SELECT ticker, name, target_price, notes, added_date "
            "FROM watchlist ORDER BY added_date DESC"
        )
        return cursor.fetchall()

    def update_watchlist_target(self, ticker, target_price, notes):
        self.conn.execute(
            "UPDATE watchlist SET target_price = ?, notes = ? WHERE ticker = ?",
            (target_price, notes, ticker),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
