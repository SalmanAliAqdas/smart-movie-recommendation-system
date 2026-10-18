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

    def genres(self, language: str = "en-US"): return self._get("/genre/movie/list", language=language).get("genres", [])
    def trending(self): return self._get("/trending/movie/week").get("results", [])
    def popular(self): return self._get("/movie/popular").get("results", [])
    def top_rated(self): return self._get("/movie/top_rated").get("results", [])
    def now_playing(self): return self._get("/movie/now_playing").get("results", [])
    def search_page(self, query: str, page: int = 1, language: str = "en-US"):
        return self._get("/search/movie", query=query.strip(), page=page, language=language, include_adult="false")

    def search(self, query: str, page: int = 1, language: str = "en-US"):
        return self.search_page(query, page, language).get("results", [])

    def discover_page(self, page: int = 1, **params):
        return self._get("/discover/movie", page=page, include_adult="false", **params)

    def discover(self, page: int = 1, **params): return self.discover_page(page, **params).get("results", [])
    def similar(self, movie_id: int): return self._get(f"/movie/{movie_id}/similar").get("results", [])

    def upcoming(self, page: int = 1, language: str = "en-US", region: str | None = None):
        params = {"page": page, "language": language}
        if region: params["region"] = region
        return self._get("/movie/upcoming", **params)

    def person_movie_credits(self, person_id: int, language: str = "en-US") -> list[dict]:
        data = self._get(f"/person/{person_id}/movie_credits", language=language)
        unique = {}
        for movie in data.get("cast", []) + data.get("crew", []):
            if movie.get("id"): unique[int(movie["id"])] = movie
        return list(unique.values())

    def collection(self, collection_id: int, language: str = "en-US") -> dict:
        return self._get(f"/collection/{collection_id}", language=language)

    def details(self, movie_id: int, language: str = "en-US", region: str = "US") -> dict:
        data = self._get(f"/movie/{movie_id}", language=language, append_to_response="credits,videos,keywords,release_dates")
        data["genre_ids"] = [g["id"] for g in data.get("genres", [])]
        data["genres"] = [g["name"] for g in data.get("genres", [])]
        data["keywords"] = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]
        credits = data.get("credits", {})
        data["cast"] = [{"id": p.get("id"), "name": p.get("name"), "character": p.get("character"), "profile_path": p.get("profile_path")} for p in credits.get("cast", [])[:8]]
        director = next((p for p in credits.get("crew", []) if p.get("job") == "Director"), None)
        data["director"] = ({"id": director.get("id"), "name": director.get("name"), "profile_path": director.get("profile_path")} if director else None)
        data["videos_list"] = data.get("videos", {}).get("results", [])
        trailer = self.select_trailer(data["videos_list"])
        data["trailer"] = trailer
        data["trailer_url"] = f"https://www.youtube.com/watch?v={trailer['key']}" if trailer else None
        data["certification"] = self.certification_for(data.get("release_dates", {}), region)
        return data

    @staticmethod
    def select_trailer(videos: list[dict]) -> dict | None:
        playable = [v for v in videos if v.get("site") == "YouTube" and v.get("key") and v.get("type") in {"Trailer", "Teaser"}]
        if not playable: return None
        return sorted(playable, key=lambda v: (v.get("type") != "Trailer", not bool(v.get("official")), -(int(v.get("size") or 0))))[0]

    @staticmethod
    def certification_for(release_dates: dict, region: str) -> str | None:
        country = next((x for x in release_dates.get("results", []) if x.get("iso_3166_1") == region), None)
        if not country: return None
        certs = [x.get("certification", "").strip() for x in country.get("release_dates", [])]
        return next((c for c in certs if c), None)

    @classmethod
    def poster_url(cls, path: str | None): return f"{cls.IMAGE_URL}{path}" if path else None

    @classmethod
    def profile_url(cls, path: str | None): return f"{cls.IMAGE_URL}{path}" if path else None

