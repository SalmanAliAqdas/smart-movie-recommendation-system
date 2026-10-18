"""SQLite persistence for one local profile, preferences, and watchlist."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

class Database:
    def __init__(self, path: str | Path = "movie_recommender.db"):
        self.path = str(path)
        self._initialize()

    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _initialize(self):
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            con.execute("""CREATE TABLE IF NOT EXISTS watchlist (
                movie_id INTEGER PRIMARY KEY, title TEXT NOT NULL, poster_path TEXT,
                release_date TEXT, status TEXT NOT NULL DEFAULT 'watchlist',
                user_rating INTEGER CHECK(user_rating BETWEEN 1 AND 5 OR user_rating IS NULL),
                metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            columns = {row[1] for row in con.execute("PRAGMA table_info(watchlist)")}
            if "created_at" not in columns:
                con.execute("ALTER TABLE watchlist ADD COLUMN created_at TEXT")
                con.execute("UPDATE watchlist SET created_at=COALESCE(created_at, updated_at, CURRENT_TIMESTAMP)")

    def save_preferences(self, values: dict):
        with self.connect() as con:
            for key, value in values.items():
                con.execute("INSERT INTO preferences(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    def get_preferences(self) -> dict:
        with self.connect() as con:
            return {row["key"]: json.loads(row["value"]) for row in con.execute("SELECT key,value FROM preferences")}

    def add_movie(self, movie: dict, status: str = "watchlist"):
        with self.connect() as con:
            con.execute("""INSERT INTO watchlist(movie_id,title,poster_path,release_date,status,metadata)
                VALUES(?,?,?,?,?,?) ON CONFLICT(movie_id) DO UPDATE SET title=excluded.title, poster_path=excluded.poster_path,
                release_date=excluded.release_date, status=excluded.status, metadata=excluded.metadata, updated_at=CURRENT_TIMESTAMP""",
                (int(movie["id"]), movie.get("title") or "Untitled", movie.get("poster_path"), movie.get("release_date"), status, json.dumps(movie)))

    def remove_movie(self, movie_id: int):
        with self.connect() as con:
            con.execute("DELETE FROM watchlist WHERE movie_id=?", (int(movie_id),))

    def update_movie(self, movie_id: int, status: str, rating: int | None = None):
        with self.connect() as con:
            con.execute("UPDATE watchlist SET status=?, user_rating=?, updated_at=CURRENT_TIMESTAMP WHERE movie_id=?", (status, rating, int(movie_id)))

    def get_watchlist(self) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM watchlist ORDER BY updated_at DESC").fetchall()
        return [dict(row) | {"metadata": json.loads(row["metadata"])} for row in rows]

    def excluded_ids(self, include_watched: bool = True, include_disliked: bool = True) -> set[int]:
        statuses = []
        if include_watched: statuses.append("watched")
        if include_disliked: statuses.append("disliked")
        if not statuses: return set()
        marks = ",".join("?" for _ in statuses)
        with self.connect() as con:
            return {int(r[0]) for r in con.execute(f"SELECT movie_id FROM watchlist WHERE status IN ({marks})", statuses)}

    def clear_all(self):
        with self.connect() as con:
            con.execute("DELETE FROM watchlist")
            con.execute("DELETE FROM preferences")

