"""Released movie discovery and fallback logic; no Streamlit or detail requests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import logging
import math
import re

from src.tmdb_client import TMDBAuthError, TMDBError

logger = logging.getLogger(__name__)
SORTS = {
    "newest": "primary_release_date.desc",
    "popular": "popularity.desc",
    "rated": "vote_average.desc",
}


class GalleryUnavailable(TMDBError):
    def __init__(self, auth_failed=False):
        self.auth_failed = auth_failed
        super().__init__("TMDB authentication failed." if auth_failed else "Movie requests are temporarily unavailable.")


@dataclass
class GalleryPage:
    movies: list[dict]
    page: int
    has_more: bool
    source: str


def usable_movies(payload, today: date | None = None) -> list[dict]:
    """Validate list metadata before it reaches poster markup or session state."""
    if isinstance(payload, dict):
        if "results" not in payload:
            raise TMDBError("TMDB movie response is missing results.")
        payload = payload["results"]
    if not isinstance(payload, list):
        raise TMDBError("TMDB movie results must be a list.")
    cutoff = today or date.today()
    result, seen = [], set()
    for movie in payload:
        if not isinstance(movie, dict):
            continue
        mid, title, path = movie.get("id"), movie.get("title"), movie.get("poster_path")
        if not isinstance(mid, int) or isinstance(mid, bool) or mid <= 0 or mid in seen:
            continue
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(path, str) or not re.fullmatch(r"/[A-Za-z0-9_-]+\.(?:jpg|png|webp)", path):
            continue
        try:
            released = date.fromisoformat(movie.get("release_date", ""))
        except (TypeError, ValueError):
            continue
        if released > cutoff or movie.get("adult") is True:
            continue
        result.append(movie)
        seen.add(mid)
    return result


def _number(movie, field):
    value = movie.get(field)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else 0.0


def sort_gallery(movies: list[dict], sort: str) -> list[dict]:
    key = {"newest": lambda m: m["release_date"],
           "popular": lambda m: _number(m, "popularity"),
           "rated": lambda m: _number(m, "vote_average")}[sort]
    return sorted(movies, key=key, reverse=True)


def load_gallery_page(client, sort="newest", page=1, language="en-US", region="US", today=None) -> GalleryPage:
    """Try recent discovery, popular, then broad discovery with identical auth."""
    if sort not in SORTS or not isinstance(page, int) or not 1 <= page <= 500:
        raise ValueError("Invalid gallery sort or page")
    today = today or date.today()
    common = {"language": language, "region": region, "sort_by": SORTS[sort],
              "primary_release_date.lte": today.isoformat(), "include_video": "false"}
    loaders = (
        ("recent_discovery", lambda: client.discover_page(page, **common, **{
            "primary_release_date.gte": (today - timedelta(days=540)).isoformat(), "vote_count.gte": 50})),
        ("popular", lambda: client.popular(language=language, page=page)),
        ("broad_discovery", lambda: client.discover_page(page, **common, **{"vote_count.gte": 10})),
    )
    for source, loader in loaders:
        try:
            payload = loader()
            movies = usable_movies(payload, today)
            if not movies:
                logger.warning("Gallery source=%s page=%s no_usable_movies=true", source, page)
                continue
            raw = payload["results"] if isinstance(payload, dict) else payload
            total = payload.get("total_pages") if isinstance(payload, dict) else None
            more = page < min(total, 500) if isinstance(total, int) else len(raw) >= 20
            return GalleryPage(sort_gallery(movies, sort), page, more, source)
        except TMDBAuthError:
            logger.warning("Gallery source=%s page=%s failure=TMDBAuthError", source, page)
            # Repeating requests with rejected credentials cannot recover authentication.
            raise GalleryUnavailable(auth_failed=True) from None
        except Exception as exc:
            # Never log arbitrary exception text/tracebacks: they may contain credentials.
            logger.warning("Gallery source=%s page=%s failure=%s", source, page, type(exc).__name__)
    raise GalleryUnavailable()


def merge_movies(existing: list[dict], incoming: list[dict], sort: str) -> list[dict]:
    unique = {movie["id"]: movie for movie in existing}
    unique.update({movie["id"]: movie for movie in incoming})
    return sort_gallery(list(unique.values()), sort)


def select_gallery_movie(movie_id, movies: list[dict]) -> dict | None:
    """Return the existing detail selection shape, including restored link selections."""
    try:
        mid = int(movie_id)
    except (TypeError, ValueError):
        return None
    if mid <= 0:
        return None
    movie = next((movie for movie in movies if movie["id"] == mid), None)
    return {"source": "home-gallery", "movie": movie or {"id": mid}}
