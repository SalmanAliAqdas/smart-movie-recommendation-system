"""Deterministic, explainable recommendation functions independent of Streamlit."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log10
from typing import Iterable

MOOD_MAPPINGS = {
    "Any": {"genres": set(), "keywords": set()},
    "Feel-good": {"genres": {35, 10751, 16, 10749}, "keywords": {"uplifting", "feel-good", "friendship"}},
    "Exciting": {"genres": {28, 12, 878}, "keywords": {"chase", "adventure", "hero"}},
    "Thought-provoking": {"genres": {18, 99, 878}, "keywords": {"society", "identity", "philosophy"}},
    "Romantic": {"genres": {10749, 18}, "keywords": {"love", "romance", "relationship"}},
    "Dark & tense": {"genres": {53, 80, 27, 9648}, "keywords": {"suspense", "conspiracy", "crime"}},
    "Family night": {"genres": {10751, 16, 12, 14}, "keywords": {"family", "magic", "friendship"}},
}

@dataclass
class Filters:
    genres: set[int] = field(default_factory=set)
    excluded_genres: set[int] = field(default_factory=set)
    mood: str = "Any"
    language: str = "Any"
    min_rating: float = 0.0
    year_min: int = 1900
    year_max: int = 2100
    runtime_min: int = 0
    runtime_max: int = 1000
    discovery: str = "Balanced"

def _genre_ids(movie: dict) -> set[int]:
    return {int(x) for x in (movie.get("genre_ids") or [])}

def _year(movie: dict) -> int | None:
    try:
        return int((movie.get("release_date") or "")[:4])
    except (TypeError, ValueError):
        return None

def passes_filters(movie: dict, filters: Filters) -> bool:
    genres = _genre_ids(movie)
    if filters.genres and not filters.genres.issubset(genres):
        return False
    if filters.excluded_genres & genres:
        return False
    if float(movie.get("vote_average") or 0) < filters.min_rating:
        return False
    year = _year(movie)
    if year is None or not filters.year_min <= year <= filters.year_max:
        return False
    runtime = movie.get("runtime")
    if runtime is not None and not filters.runtime_min <= int(runtime) <= filters.runtime_max:
        return False
    if filters.language != "Any" and movie.get("original_language") != filters.language:
        return False
    return True

def score_movie(movie: dict, filters: Filters, favorite_genres: set[int] | None = None, seed: dict | None = None) -> tuple[float, list[str]]:
    genres = _genre_ids(movie)
    reasons: list[str] = []
    score = 0.0
    matched = genres & filters.genres
    if matched:
        score += 5.0 * len(matched) / max(len(filters.genres), 1)
        reasons.append(f"matches {len(matched)} selected genre{'s' if len(matched) != 1 else ''}")
    favorites = genres & (favorite_genres or set())
    if favorites:
        score += 1.5 * len(favorites)
        reasons.append("fits your favourite genres")
    mood = MOOD_MAPPINGS.get(filters.mood, MOOD_MAPPINGS["Any"])
    mood_genres = genres & mood["genres"]
    keywords = {str(k).lower() for k in (movie.get("keywords") or [])}
    mood_keywords = keywords & mood["keywords"]
    if mood_genres or mood_keywords:
        score += 2.0 + 0.3 * len(mood_keywords)
        reasons.append(f"fits the {filters.mood.lower()} mood mapping")
    if filters.language != "Any" and movie.get("original_language") == filters.language:
        score += 1.0
        reasons.append("is in your preferred language")
    rating = float(movie.get("vote_average") or 0)
    votes = int(movie.get("vote_count") or 0)
    reliability = min(1.0, log10(votes + 1) / 3.0)
    score += (rating / 2.0) * reliability
    if rating >= 7 and votes >= 100:
        reasons.append(f"is well rated ({rating:.1f} from {votes:,} votes)")
    popularity = float(movie.get("popularity") or 0)
    pop_component = min(popularity, 100) / 100
    if filters.discovery == "Popular":
        score += 2.0 * pop_component
        reasons.append("has strong audience interest")
    elif filters.discovery == "Hidden gems":
        score += 2.0 * (1 - pop_component) * reliability
        reasons.append("is a less prominent discovery")
    else:
        score += pop_component
    if seed:
        shared_genres = genres & _genre_ids(seed)
        shared_keywords = keywords & {str(k).lower() for k in (seed.get("keywords") or [])}
        score += 2.0 * len(shared_genres) + 0.75 * len(shared_keywords)
        if shared_genres:
            reasons.append(f"shares {len(shared_genres)} genre{'s' if len(shared_genres) != 1 else ''} with {seed.get('title', 'your pick')}")
        if shared_keywords:
            reasons.append("shares story themes with your pick")
    return round(score, 4), reasons or ["meets your selected filters"]

def recommend(movies: Iterable[dict], filters: Filters, limit: int = 10, favorite_genres: set[int] | None = None, excluded_ids: set[int] | None = None, seed: dict | None = None) -> list[dict]:
    excluded_ids = excluded_ids or set()
    unique: dict[int, dict] = {}
    for movie in movies:
        movie_id = movie.get("id")
        if movie_id is None or int(movie_id) in excluded_ids or not passes_filters(movie, filters):
            continue
        unique[int(movie_id)] = movie
    ranked = []
    for movie in unique.values():
        score, reasons = score_movie(movie, filters, favorite_genres, seed)
        ranked.append({**movie, "recommendation_score": score, "reasons": reasons})
    return sorted(ranked, key=lambda m: (-m["recommendation_score"], -float(m.get("vote_count") or 0), int(m["id"])))[:limit]

