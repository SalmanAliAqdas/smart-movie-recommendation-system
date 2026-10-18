"""Preference defaults and normalization."""

DEFAULTS = {"favorite_genres": [], "excluded_genres": [], "language": "Any", "min_rating": 6.0, "interface_language": "en"}

def merged_preferences(saved: dict | None) -> dict:
    return DEFAULTS | (saved or {})

