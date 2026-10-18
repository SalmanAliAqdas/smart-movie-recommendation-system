"""Fault-isolated loading for the Explore homepage's live TMDB shelves."""
from __future__ import annotations
from collections.abc import Callable
from datetime import date
import logging

logger = logging.getLogger(__name__)

SECTION_KEYS = ("latest", "trending", "popular", "top_rated", "upcoming")

def _movie_list(payload) -> list[dict]:
    if isinstance(payload, dict):
        payload = payload.get("results", [])
    if not isinstance(payload, list):
        raise TypeError("TMDB section response must be a movie list or results object")
    return [movie for movie in payload if isinstance(movie, dict) and movie.get("id")]

def released_newest_first(movies: list[dict], today: date | None = None) -> list[dict]:
    """Keep released titles only and put the newest dated releases first."""
    cutoff = (today or date.today()).isoformat()
    released = [movie for movie in movies if movie.get("release_date") and movie["release_date"] <= cutoff]
    return sorted(released, key=lambda movie: movie["release_date"], reverse=True)

def _section_loaders(client, language: str, region: str) -> dict[str, Callable]:
    return {
        "latest": lambda: released_newest_first(_movie_list(client.now_playing(language=language, region=region))),
        "trending": lambda: client.trending(language=language),
        "popular": lambda: client.popular(language=language),
        "top_rated": lambda: client.top_rated(language=language),
        "upcoming": lambda: client.upcoming(language=language, region=region),
    }

def complete_homepage_sections(
    client, sections: dict | None, errors: dict | None,
    language: str = "en-US", region: str = "US",
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Enforce the shelf schema and refresh keys absent from older cached results."""
    sections = sections if isinstance(sections, dict) else {}
    errors = errors if isinstance(errors, dict) else {}
    loaders = _section_loaders(client, language, region)
    complete, section_errors = {}, {}
    for key in SECTION_KEYS:
        try:
            payload = sections[key] if key in sections else loaders[key]()
            complete[key] = _movie_list(payload)
            if key in errors:
                section_errors[key] = str(errors[key])
        except Exception as exc:
            logger.warning("Homepage section=%s failure=%s", key, type(exc).__name__)
            complete[key] = []
            section_errors[key] = str(exc)
    return complete, section_errors

def load_homepage_sections(client, language: str = "en-US", region: str = "US") -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Load each shelf independently so one failed endpoint cannot blank the page."""
    return complete_homepage_sections(client, {}, {}, language, region)
