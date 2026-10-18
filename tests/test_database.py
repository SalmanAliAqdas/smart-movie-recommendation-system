from src.database import Database

MOVIE = {"id": 7, "title": "Test Movie", "release_date": "2020-01-01", "poster_path": None}

def test_watchlist_crud_and_no_duplicates(tmp_path):
    db = Database(tmp_path / "test.db")
    db.add_movie(MOVIE); db.add_movie(MOVIE)
    assert len(db.get_watchlist()) == 1
    db.update_movie(7, "watched", 4)
    assert db.get_watchlist()[0]["user_rating"] == 4
    assert db.excluded_ids() == {7}
    db.remove_movie(7)
    assert db.get_watchlist() == []

def test_preferences_and_clear(tmp_path):
    db = Database(tmp_path / "test.db")
    db.save_preferences({"language": "fr", "genres": [35]})
    assert db.get_preferences()["language"] == "fr"
    db.add_movie(MOVIE); db.clear_all()
    assert db.get_preferences() == {} and db.get_watchlist() == []

def test_existing_database_migrates_created_at(tmp_path):
    import sqlite3
    path=tmp_path / "old.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("CREATE TABLE watchlist (movie_id INTEGER PRIMARY KEY, title TEXT NOT NULL, poster_path TEXT, release_date TEXT, status TEXT, user_rating INTEGER, metadata TEXT, updated_at TEXT)")
        con.execute("INSERT INTO watchlist VALUES (1,'Old',NULL,'2020-01-01','watchlist',NULL,'{}','2025-01-01')")
    row=Database(path).get_watchlist()[0]
    assert row["title"] == "Old" and row["created_at"] == "2025-01-01"

