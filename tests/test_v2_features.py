from datetime import date
import csv, io
from src.catalog import certification_allowed, comparison_winner, filter_movies, in_collection, is_upcoming, page_items, sort_movies
from src.i18n import tr
from src.tmdb_client import TMDBClient
from src.watchlist_export import watchlist_csv

MOVIES = [
    {"id":1,"title":"A","release_date":"2022-01-01","genre_ids":[35],"original_language":"en","vote_average":7.0,"vote_count":500,"runtime":90,"popularity":10,"production_countries":[{"iso_3166_1":"US"}]},
    {"id":2,"title":"B","release_date":"2024-01-01","genre_ids":[18],"original_language":"ko","vote_average":8.0,"vote_count":1000,"runtime":130,"popularity":30,"production_countries":[{"iso_3166_1":"KR"}]},
]

def test_advanced_filtering_sorting_and_pagination():
    assert [m["id"] for m in filter_movies(MOVIES, genres={35}, votes=100, runtime_max=100, country="US")] == [1]
    assert [m["id"] for m in sort_movies(MOVIES, "Highest rated")] == [2,1]
    assert page_items(list(range(25)), 2, 10) == list(range(10,20))

def test_trailer_selection_prefers_official_trailer():
    videos = [{"key":"tease","site":"YouTube","type":"Teaser","official":True}, {"key":"fan","site":"YouTube","type":"Trailer","official":False}, {"key":"official","site":"YouTube","type":"Trailer","official":True}]
    assert TMDBClient.select_trailer(videos)["key"] == "official"
    assert TMDBClient.select_trailer([]) is None

def test_certification_and_upcoming_and_comparison():
    assert certification_allowed("PG", "US", True)
    assert not certification_allowed(None, "US", True)
    assert is_upcoming({"release_date":"2999-01-01"}, date(2026,1,1))
    assert comparison_winner(MOVIES[0], MOVIES[1]) == "B"

def test_translations_and_collection_membership():
    assert tr("Discover", "ur") == "دریافت کریں"
    assert tr("Discover", "en") == "Discover"
    assert in_collection({"belongs_to_collection":{"id":4,"name":"Saga"}})
    assert not in_collection({"belongs_to_collection":None})

def test_watchlist_csv_utf8_bom_and_fields():
    rows=[{"title":"فلم","release_date":"2020-01-01","user_rating":5,"status":"watched","created_at":"2026-01-01","metadata":{"genres":["Drama"],"vote_average":8.2}}]
    payload=watchlist_csv(rows)
    assert payload.startswith(b"\xef\xbb\xbf")
    parsed=list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    assert parsed[0]["title"] == "فلم" and parsed[0]["personal_rating"] == "5"

