"""Pure helpers for filtering, sorting, paging, certifications, and comparisons."""
from __future__ import annotations
from datetime import date

SORTS = {
    "Popularity": lambda m: -float(m.get("popularity") or 0),
    "Highest rated": lambda m: -float(m.get("vote_average") or 0),
    "Most votes": lambda m: -int(m.get("vote_count") or 0),
    "Newest release": lambda m: m.get("release_date") or "0000-00-00",
    "Oldest release": lambda m: m.get("release_date") or "9999-99-99",
}

FAMILY_CERTIFICATIONS = {
    "US": {"G", "PG", "TV-Y", "TV-Y7", "TV-G", "TV-PG"},
    "GB": {"U", "PG"},
    "PK": {"U", "PG"},
    "IN": {"U", "U/A", "UA"},
    "CA": {"G", "PG"},
    "AU": {"G", "PG"},
}

def filter_movies(movies: list[dict], *, genres: set[int] | None = None, excluded: set[int] | None = None,
                  year_min: int = 0, year_max: int = 9999, language: str = "Any", rating: float = 0,
                  votes: int = 0, runtime_min: int = 0, runtime_max: int = 10_000,
                  country: str = "Any", released_only: bool = False) -> list[dict]:
    wanted, excluded = genres or set(), excluded or set()
    today = date.today().isoformat()
    result = []
    for movie in movies:
        ids = {int(x) for x in movie.get("genre_ids", [])}
        raw_year = (movie.get("release_date") or "")[:4]
        if not raw_year.isdigit(): continue
        runtime = movie.get("runtime")
        countries = {x.get("iso_3166_1") if isinstance(x, dict) else x for x in movie.get("production_countries", [])}
        if wanted and not wanted.issubset(ids): continue
        if ids & excluded: continue
        if not year_min <= int(raw_year) <= year_max: continue
        if language != "Any" and movie.get("original_language") != language: continue
        if float(movie.get("vote_average") or 0) < rating or int(movie.get("vote_count") or 0) < votes: continue
        if runtime is not None and not runtime_min <= int(runtime) <= runtime_max: continue
        if country != "Any" and country not in countries: continue
        if released_only and (movie.get("release_date") or "9999-99-99") > today: continue
        result.append(movie)
    return result

def sort_movies(movies: list[dict], sort_name: str) -> list[dict]:
    reverse = sort_name == "Newest release"
    return sorted(movies, key=SORTS.get(sort_name, SORTS["Popularity"]), reverse=reverse)

def page_items(items: list[dict], page: int, per_page: int = 12) -> list[dict]:
    if page < 1 or per_page < 1: return []
    start = (page - 1) * per_page
    return items[start:start + per_page]

def certification_allowed(certification: str | None, region: str, family_mode: bool, selected: set[str] | None = None) -> bool:
    if not family_mode: return True
    if not certification: return False
    allowed = selected or FAMILY_CERTIFICATIONS.get(region, set())
    return certification.upper() in {x.upper() for x in allowed}

def comparison_winner(left: dict, right: dict) -> str | None:
    a, b = float(left.get("vote_average") or 0), float(right.get("vote_average") or 0)
    if a == b: return None
    return left.get("title") if a > b else right.get("title")

def is_upcoming(movie: dict, today: date | None = None) -> bool:
    return bool(movie.get("release_date") and movie["release_date"] > (today or date.today()).isoformat())

def in_collection(movie: dict) -> bool:
    collection = movie.get("belongs_to_collection")
    return isinstance(collection, dict) and bool(collection.get("id") and collection.get("name"))

