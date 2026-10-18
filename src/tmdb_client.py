"""Resilient TMDB API client. No UI dependencies and no credential persistence."""
from __future__ import annotations
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TMDBError(RuntimeError): pass
class TMDBAuthError(TMDBError): pass
class TMDBRateLimitError(TMDBError): pass

class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_URL = "https://image.tmdb.org/t/p/w500"

    def __init__(self, api_key: str | None = None, read_token: str | None = None, timeout: float = 10, session=None):
        if not api_key and not read_token:
            raise ValueError("A TMDB API key or read access token is required")
        self.api_key, self.read_token, self.timeout = api_key, read_token, timeout
        self.session = session or requests.Session()
        if session is None:
            retry = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
            self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _get(self, path: str, **params):
        headers = {"accept": "application/json"}
        if self.read_token: headers["Authorization"] = f"Bearer {self.read_token}"
        if self.api_key: params["api_key"] = self.api_key
        try:
            response = self.session.get(f"{self.BASE_URL}{path}", params=params, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TMDBError(f"Could not reach TMDB: {exc}") from exc
        if response.status_code in (401, 403): raise TMDBAuthError("TMDB rejected the credential. Check your API key or read token.")
        if response.status_code == 429: raise TMDBRateLimitError("TMDB rate limit reached. Please wait and try again.")
        try: response.raise_for_status()
        except requests.RequestException as exc: raise TMDBError(f"TMDB returned HTTP {response.status_code}.") from exc
        try: return response.json()
        except ValueError as exc: raise TMDBError("TMDB returned an invalid response.") from exc

    def genres(self): return self._get("/genre/movie/list").get("genres", [])
    def trending(self): return self._get("/trending/movie/week").get("results", [])
    def popular(self): return self._get("/movie/popular").get("results", [])
    def top_rated(self): return self._get("/movie/top_rated").get("results", [])
    def now_playing(self): return self._get("/movie/now_playing").get("results", [])
    def search(self, query: str): return self._get("/search/movie", query=query, include_adult="false").get("results", [])
    def discover(self, **params): return self._get("/discover/movie", include_adult="false", **params).get("results", [])
    def similar(self, movie_id: int): return self._get(f"/movie/{movie_id}/similar").get("results", [])

    def details(self, movie_id: int) -> dict:
        data = self._get(f"/movie/{movie_id}", append_to_response="credits,videos,keywords")
        data["genre_ids"] = [g["id"] for g in data.get("genres", [])]
        data["genres"] = [g["name"] for g in data.get("genres", [])]
        data["keywords"] = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]
        credits = data.get("credits", {})
        data["cast"] = [p["name"] for p in credits.get("cast", [])[:5]]
        data["director"] = next((p["name"] for p in credits.get("crew", []) if p.get("job") == "Director"), None)
        trailers = [v for v in data.get("videos", {}).get("results", []) if v.get("site") == "YouTube" and v.get("type") == "Trailer"]
        data["trailer_url"] = f"https://www.youtube.com/watch?v={trailers[0]['key']}" if trailers else None
        return data

    @classmethod
    def poster_url(cls, path: str | None): return f"{cls.IMAGE_URL}{path}" if path else None

