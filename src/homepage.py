"""Fault-isolated loading for the Explore homepage's live TMDB shelves."""
from __future__ import annotations
from collections.abc import Callable

SECTION_KEYS = ("trending", "popular", "top_rated", "now_playing", "upcoming")

def _movie_list(payload) -> list[dict]:
    if isinstance(payload, dict):
        payload = payload.get("results", [])
    if not isinstance(payload, list):
        raise TypeError("TMDB section response must be a movie list or results object")
    return [movie for movie in payload if isinstance(movie, dict) and movie.get("id")]

def load_homepage_sections(client, language: str = "en-US", region: str = "US") -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Load each shelf independently so one failed endpoint cannot blank the page."""
    loaders: dict[str, Callable] = {
        "trending": lambda: client.trending(language=language),
        "popular": lambda: client.popular(language=language),
        "top_rated": lambda: client.top_rated(language=language),
        "now_playing": lambda: client.now_playing(language=language, region=region),
        "upcoming": lambda: client.upcoming(language=language, region=region),
    }
    sections, errors = {}, {}
    for key, loader in loaders.items():
        try:
            sections[key] = _movie_list(loader())
        except Exception as exc:
            sections[key] = []
            errors[key] = str(exc)
    return sections, errors
