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

