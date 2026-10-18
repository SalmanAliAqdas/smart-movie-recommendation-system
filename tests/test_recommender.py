from src.demo_data import DEMO_MOVIES
from src.recommender import Filters, passes_filters, recommend, score_movie

def test_genre_and_multi_genre_filtering():
    assert passes_filters(DEMO_MOVIES[0], Filters(genres={12}))
    assert passes_filters(DEMO_MOVIES[0], Filters(genres={12, 878}))
    assert not passes_filters(DEMO_MOVIES[0], Filters(genres={12, 35}))

def test_rating_threshold_and_exclusion():
    assert not passes_filters(DEMO_MOVIES[4], Filters(min_rating=7.0))
    assert not passes_filters(DEMO_MOVIES[0], Filters(excluded_genres={878}))

def test_scoring_is_deterministic_and_explainable():
    filters = Filters(genres={12}, mood="Exciting")
    first = score_movie(DEMO_MOVIES[0], filters)
    assert first == score_movie(DEMO_MOVIES[0], filters)
    assert first[0] > 0 and first[1]

def test_duplicate_removal_and_excluded_ids():
    movies = [DEMO_MOVIES[0], dict(DEMO_MOVIES[0]), DEMO_MOVIES[1]]
    results = recommend(movies, Filters(), excluded_ids={DEMO_MOVIES[1]["id"]})
    assert [m["id"] for m in results] == [DEMO_MOVIES[0]["id"]]

def test_missing_metadata_and_empty_results():
    assert recommend([{"id": 999}], Filters()) == []  # missing year fails safely
    assert recommend([], Filters()) == []

def test_demo_mode_catalog_recommends():
    results = recommend(DEMO_MOVIES, Filters(year_min=1900, year_max=2100, runtime_max=300))
    assert results and all(m.get("demo") for m in results)

