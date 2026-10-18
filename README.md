# CineMatch — Smart Movie Recommendation System

CineMatch is a polished Streamlit movie-discovery app with explainable, deterministic recommendations. It combines TMDB metadata with genre, mood, language, rating, year, runtime and discovery-style preferences. A local SQLite database stores a single local profile, watchlist, watched state, dislikes and 1–5 star ratings.

## Features

- Cinematic dashboard with trending, highly rated and currently playing movies
- Title search and complete movie details, including cast, director and trailer when TMDB provides them
- Multi-genre recommendations with hard exclusions and transparent per-movie reasons
- Similar-movie ranking using shared genres and available keywords
- Persistent local preferences and watchlist, watched/disliked states and personal ratings
- “Surprise me” from the current eligible recommendation set
- Explicit demo mode with eight fictional, metadata-only movies and no copyrighted posters
- Resilient TMDB client with timeouts, retry/backoff, caching, rate-limit handling and clear errors
- Responsive dark Streamlit interface

## Screenshots

Screenshots are not included because no browser screenshot was captured for this repository.

## Requirements

- Python 3.11 or newer
- A free TMDB API credential for live data (optional for demo mode)

## Installation and local execution (PowerShell)

```powershell
cd "C:\Users\SALMAN\Downloads\Smart Movie Recommendation System"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

## TMDB API setup

Create a free TMDB account and request API access from the TMDB account settings. Use either the v4 Read Access Token (recommended) or the v3 API key. Copy `.env.example` to `.env`, then add one credential:

```dotenv
TMDB_READ_ACCESS_TOKEN=your_read_access_token
# or: TMDB_API_KEY=your_v3_api_key
DEMO_MODE=false
```

Never commit `.env` or `.streamlit/secrets.toml`; both are ignored. For Streamlit Community Cloud, add the same name and value in the app's Secrets settings. The app reads Streamlit secrets first and environment variables second.

## Demo mode

With no credential, CineMatch clearly labels itself **Demo Catalog** and uses fictional movie records without poster assets. Set `DEMO_MODE=true` to force demo mode even when a credential exists. If live TMDB requests fail, the app reports the failure and does not silently replace results with demo records.

## Recommendation methodology

The engine first applies hard filters: every selected genre must match, excluded genres must not match, and rating, language, year and available runtime must meet the selected ranges. It removes duplicate IDs and optionally removes watched/disliked titles.

Remaining movies receive a deterministic content score from selected and favourite genres, the documented mood-to-genre/keyword mapping, language, rating, vote count, popularity preference and—on Similar Movies—shared genres and keywords. Rating influence is reduced for titles with few votes, preventing a tiny sample from being treated like a well-established rating. Score ties use vote count and movie ID. The UI displays plain-language reasons for each result.

TMDB does not provide a reliable mood classification. CineMatch's mood choices are transparent heuristics listed on the Settings page.

## Testing

```powershell
python -m pytest -q
python -m compileall app.py src tests
```

Tests cover genre and multi-genre filtering, rating thresholds, excluded genres, deterministic scoring, duplicate removal, watched exclusions, missing metadata, empty results, SQLite operations, demo data, successful mocked API responses, invalid credentials and malformed API responses.

## Deployment guidance

1. Push the source to a private or public GitHub repository, ensuring `.env`, secrets and `*.db` are absent.
2. In Streamlit Community Cloud, create an app pointing to `app.py`.
3. Add `TMDB_READ_ACCESS_TOKEN` (or `TMDB_API_KEY`) in the Cloud app's Secrets settings.
4. Deploy using the included `requirements.txt`.

SQLite is local-process storage. Streamlit Community Cloud may restart or replace the app filesystem, so watchlist and preference persistence is not guaranteed there and is not shared across devices. This version has one local profile and does not provide authentication or secure independent user accounts. Use a hosted database plus authentication before treating it as a multi-user service.

## Limitations

- Recommendations use metadata heuristics, not collaborative filtering or trained machine learning.
- TMDB metadata can be incomplete; missing runtime, artwork, cast, director and trailers are handled gracefully.
- Provider availability is intentionally not claimed or scraped.
- Search and discovery depend on TMDB availability and limits in live mode.
- The demo catalog is deliberately small and fictional.

## Attribution and licensing notes

This product uses the TMDB API but is not endorsed or certified by TMDB. Live movie metadata and images are supplied by TMDB and remain subject to TMDB's terms and image usage requirements. The demo movie names, people and descriptions are fictional and contain no redistributed poster artwork.

Application source code may be licensed by the repository owner. No license is granted here for third-party TMDB data or imagery.

