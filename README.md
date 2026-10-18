# CineMatch 2.0 — Smart Movie Recommendation System

CineMatch is a cinematic Streamlit application for discovering real movies through TMDB metadata and transparent, deterministic recommendations. Version 2.0 adds advanced discovery, upcoming releases, cast and director exploration, official collections, comparison, regional family-certification filters, English/Urdu interface support, and CSV watchlist export.

## Features

- **Discover:** an automatically loaded Explore Movies poster gallery, compact title search, three gallery sort modes and Load More. Advanced Discovery retains pagination, genres, excluded genres, release years, original language, minimum TMDB rating and vote count, runtime, origin country, and five sort modes.
- **Recommendations:** deterministic content scoring with genre, mood, language, rating reliability, popularity, preference, runtime and watched/disliked exclusions. Every result includes reasons.
- **Movie details:** overview, genres, runtime, original language, TMDB rating and vote count, director, main cast, character names, regional certification, TMDB link, and a preferred official YouTube trailer or teaser.
- **People:** cached actor/director filmographies with profile photographs when TMDB supplies them.
- **Upcoming:** region-aware upcoming results, genre/language filters, release-date sorting and changeable-release-date notices.
- **Compare:** side-by-side metadata for two different films, including a carefully qualified TMDB user-rating comparison.
- **Family mode:** region-specific certification filtering. Missing certifications are excluded rather than guessed, and suitability is never guaranteed.
- **Urdu interface:** Settings can switch common navigation, actions, filters and messages between English and Urdu. Urdu layout uses right-to-left presentation where practical. Movie metadata uses TMDB localization and falls back without invented translations.
- **Collections:** official TMDB franchise membership and chronologically sorted parts; similar movies are never mislabeled as franchise entries.
- **Watchlist:** SQLite-backed watchlist, watched/disliked state, personal 1–5 rating, removal, and an in-memory UTF-8-with-BOM CSV export.
- **Demo mode:** eight fictional metadata-only films with no redistributed poster assets.

## Architecture

```text
app.py                       Streamlit entrypoint and UI orchestration
src/tmdb_client.py           Resilient official TMDB API client
src/gallery.py               Released movie validation, discovery, fallbacks and pagination
src/gallery_view.py          Responsive poster markup and scoped gallery styles
src/recommender.py           Explainable recommendation filtering/scoring
src/catalog.py               Advanced filters, sorting, paging and comparisons
src/i18n.py                  English and Urdu interface strings
src/database.py              Backward-compatible SQLite persistence
src/watchlist_export.py      In-memory CSV generation
src/demo_data.py             Fictional credential-free catalog
tests/                       Unit and mocked API tests
```

## Requirements and installation

- Python 3.11 or newer
- Optional free TMDB API credential for live mode

```powershell
cd "C:\Users\SALMAN\Downloads\Smart Movie Recommendation System"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

Streamlit normally opens `http://localhost:8501`.

## TMDB setup

Obtain a credential from the TMDB account API settings. Put a v4 Read Access Token (recommended) or v3 key in the untracked `.env` file:

```dotenv
TMDB_READ_ACCESS_TOKEN=your_read_access_token
# Or: TMDB_API_KEY=your_v3_api_key
DEMO_MODE=false
```

The app checks Streamlit secrets first and environment variables second. It never stores credentials in SQLite. `.env`, Streamlit secret files, virtual environments and local databases are excluded by `.gitignore`.

For Streamlit Community Cloud, configure one of these in the app's Secrets panel:

```toml
TMDB_READ_ACCESS_TOKEN = "your_read_access_token"
DEMO_MODE = "false"
```

No source-code change or new deployment URL is required when upgrading the existing app; `app.py` remains the entrypoint.

## Homepage gallery and diagnostics

The gallery uses the existing authenticated TMDB client. It first discovers movies released within the past 540 days with at least 50 votes, then tries popular movies, then broader released-movie discovery with at least 10 votes. All results must have a title, a TMDB poster path and a valid release date no later than today. Sorting applies to the TMDB discovery query and the displayed results. TMDB pages contain up to 20 movies; Load More appends and deduplicates successive pages without requesting full details for every poster.

Successful pages are cached for ten minutes, scoped by credentials, date, language, region, sort and source versions. Session state retains previously loaded movies if a later request fails. Errors are not cached. Authentication failures are reported explicitly; they do not trigger fake content. Without credentials, the homepage shows one setup message and Retry; the other features retain their existing demo behavior. Poster links open the existing details interface.

Earlier homepage shelves hid all exceptions behind identical warnings and cached failed section results for 15 minutes. The gallery logs endpoint paths, HTTP status codes, source names and exception types without query strings, credentials, response bodies or tracebacks. The cached client is keyed by its source fingerprint so an old resource cannot retain missing movie-list methods after an update. To diagnose a deployment failure, inspect its Streamlit logs for `TMDB endpoint=` and `Gallery source=` entries; local tests cannot establish a production HTTP failure without deployment logs or live credentials.

The gallery layout uses its own CSS classes rather than Streamlit column internals. Advanced Discovery runs when its form is submitted so collapsed filters do not issue an extra discovery request during initial gallery loading.

## Advanced search behavior

Title Search uses TMDB's movie-title search endpoint and does not pretend it accepts discovery-only constraints. Advanced Discovery uses TMDB's discovery endpoint and applicable server-side parameters, followed by conservative local checks when enriched details are needed. “Load more” advances through TMDB result pages. Unreleased films are clearly marked only in Upcoming; the app makes no claim about cinema or streaming availability.

## Recommendations

Recommendations apply hard filters before deterministic scoring. TMDB rating influence is discounted when vote counts are small. Mood is an openly documented genre/keyword heuristic, not a TMDB mood classification.

## Family-certification limitations

Certifications come from TMDB regional release-date records and can be absent, inconsistent, or different between regions. Family mode requires an allowed certification and excludes unclassified results. Genre alone is never treated as proof of age suitability. Parents and guardians should independently verify each film.

## Watchlist persistence and privacy

The schema migration adds `created_at` without deleting existing records. CSV downloads are generated in memory and include title, release year, genres, TMDB rating, personal rating, status and date added.

This version has one SQLite database and no authentication. On a public Streamlit deployment, the watchlist may be shared between visitors, and Community Cloud local filesystem data is not guaranteed to persist across restarts or redeployments. Do not treat it as private per-user storage.

## Testing

```powershell
python -m pytest -q
python -m compileall -q app.py src tests
python -m streamlit run app.py --server.headless true
```

The test suite covers original recommendations and watchlist behavior plus advanced filtering/sorting, pagination, official trailer preference, cast/director parsing, upcoming dates, comparison, certification filtering, English/Urdu strings, collection membership, BOM-safe CSV export, API errors, missing data and legacy database migration. TMDB tests use mocked responses and require no credentials.

## Limitations

- Metadata, images, localized text, videos, certifications and release dates depend on TMDB completeness.
- Urdu interface coverage focuses on common interaction strings; movie metadata is never machine-invented.
- The demo catalog cannot demonstrate live-only people, upcoming, certification or official collection endpoints.
- Recommendations are metadata heuristics, not collaborative filtering or trained machine learning.
- Provider/streaming availability is intentionally not claimed or scraped.

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. Live movie metadata and imagery are supplied by TMDB and remain subject to TMDB's terms and image usage requirements. YouTube trailers are embedded or linked; they are not downloaded or redistributed. Demo titles and people are fictional.
