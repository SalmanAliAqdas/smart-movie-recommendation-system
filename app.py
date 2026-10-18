from __future__ import annotations
import os, random
from datetime import date
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from src.database import Database
from src.demo_data import DEMO_MOVIES, GENRES
from src.preferences import merged_preferences
from src.recommender import Filters, MOOD_MAPPINGS, recommend
from src.tmdb_client import TMDBClient, TMDBError

load_dotenv()
st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');
.stApp{background:radial-gradient(circle at 80% 0%,#2b1539 0,#0c0d13 34%,#08090d 100%);color:#f4f1eb}.block-container{max-width:1400px;padding-top:2rem}.hero{padding:2.7rem;border:1px solid #ffffff1a;border-radius:24px;background:linear-gradient(120deg,#171824ee,#38152dcc);margin-bottom:1.4rem}.hero h1{font-family:'Playfair Display';font-size:3.5rem;margin:0}.eyebrow{color:#f6af45;letter-spacing:.18em;font-weight:700;font-size:.78rem}.movie-card{background:#15161e;border:1px solid #ffffff14;border-radius:18px;overflow:hidden;padding:1rem;min-height:360px;box-shadow:0 12px 32px #0005}.poster-placeholder{height:190px;border-radius:12px;background:linear-gradient(145deg,#542343,#171827);display:flex;align-items:center;justify-content:center;font-size:3rem}.meta{color:#aaa9b4;font-size:.84rem}.score{color:#f6af45;font-weight:700}.demo-pill{background:#f6af4520;color:#f6af45;padding:.25rem .6rem;border-radius:999px;font-size:.75rem}.stButton>button{border-radius:999px}.attribution{font-size:.78rem;color:#8d8d99;padding-top:2rem}h1,h2,h3{font-family:'DM Sans',sans-serif}
</style>""", unsafe_allow_html=True)

def secret(name):
    try: return st.secrets.get(name) or os.getenv(name)
    except Exception: return os.getenv(name)

forced_demo = str(secret("DEMO_MODE") or "").lower() == "true"
token, api_key = secret("TMDB_READ_ACCESS_TOKEN"), secret("TMDB_API_KEY")
demo_mode = forced_demo or not (token or api_key)
db = Database(Path(__file__).with_name("movie_recommender.db"))
prefs = merged_preferences(db.get_preferences())

@st.cache_resource
def live_client(key, tok): return TMDBClient(api_key=key, read_token=tok)
client = None if demo_mode else live_client(api_key, token)

@st.cache_data(ttl=3600, show_spinner=False)
def genres_live(): return {g["id"]: g["name"] for g in client.genres()}
@st.cache_data(ttl=900, show_spinner=False)
def details_live(mid): return client.details(mid)

genre_map = GENRES
if client:
    try: genre_map = genres_live()
    except TMDBError as exc: st.error(str(exc)); st.stop()
name_to_id = {name: gid for gid, name in genre_map.items()}

def hydrate(movie):
    if demo_mode: return movie
    try: return details_live(int(movie["id"]))
    except TMDBError: return movie

def poster(movie):
    path = movie.get("poster_path")
    if path and client: st.image(client.poster_url(path), use_container_width=True)
    else: st.markdown('<div class="poster-placeholder">🎞️</div>', unsafe_allow_html=True)

def add_button(movie, key):
    if st.button("＋ Watchlist", key=key, use_container_width=True):
        db.add_movie(movie); st.toast(f"Added {movie.get('title', 'movie')}")

def card(movie, key):
    poster(movie)
    year = (movie.get("release_date") or "Unknown")[:4]
    rating = movie.get("vote_average")
    st.markdown(f"### {movie.get('title') or 'Untitled'}")
    st.markdown(f'<div class="meta">{year} · {movie.get("original_language", "—").upper()} · ⭐ {rating:.1f}</div>' if isinstance(rating,(int,float)) else f'<div class="meta">{year}</div>', unsafe_allow_html=True)
    if movie.get("reasons"): st.caption("Why: " + "; ".join(movie["reasons"][:2]) + ".")
    add_button(movie, key)

def grid(movies, prefix, count=6):
    if not movies: st.info("No movies matched. Try broadening the filters."); return
    cols = st.columns(min(3, len(movies)))
    for i, movie in enumerate(movies[:count]):
        with cols[i % len(cols)]:
            with st.container(border=True): card(movie, f"{prefix}-{movie['id']}-{i}")

def show_details(movie):
    movie = hydrate(movie)
    left, right = st.columns([1, 2])
    with left: poster(movie); add_button(movie, f"detail-{movie['id']}")
    with right:
        st.title(movie.get("title") or "Untitled")
        if movie.get("original_title") and movie["original_title"] != movie.get("title"): st.caption(movie["original_title"])
        st.write(" · ".join(filter(None, [(movie.get("release_date") or "")[:4], ", ".join(movie.get("genres") or []), f"{movie.get('runtime')} min" if movie.get("runtime") else None, (movie.get("original_language") or "").upper()])))
        st.write(f"⭐ {float(movie.get('vote_average') or 0):.1f} · {int(movie.get('vote_count') or 0):,} votes")
        st.write(movie.get("overview") or "No synopsis is available.")
        if movie.get("director"): st.write("**Director:**", movie["director"])
        if movie.get("cast"): st.write("**Main cast:**", ", ".join(movie["cast"]))
        links = [f"[View on TMDB](https://www.themoviedb.org/movie/{movie['id']})"]
        if movie.get("trailer_url"): links.append(f"[Watch trailer]({movie['trailer_url']})")
        st.markdown(" · ".join(links))

with st.sidebar:
    st.markdown("## 🎬 CineMatch")
    st.caption("Your next great watch, explained.")
    page = st.radio("Navigate", ["Discover", "Recommendations", "Similar Movies", "Watchlist", "Settings"], label_visibility="collapsed")
    st.divider()
    st.markdown('<span class="demo-pill">DEMO CATALOG</span>' if demo_mode else '<span class="demo-pill">LIVE TMDB</span>', unsafe_allow_html=True)
    if demo_mode: st.caption("Using fictional metadata-only sample movies. Add a TMDB credential for live results.")

if page == "Discover":
    st.markdown('<section class="hero"><div class="eyebrow">CURATED MOVIE DISCOVERY</div><h1>Find a story worth staying up for.</h1><p>Search, explore and save films with recommendations you can actually understand.</p></section>', unsafe_allow_html=True)
    query = st.text_input("Search movies", placeholder="Search by title…", icon="🔎")
    if query:
        if demo_mode: results = [m for m in DEMO_MOVIES if query.lower() in m["title"].lower()]
        else:
            try:
                with st.spinner("Searching TMDB…"): results = client.search(query)
            except TMDBError as exc: st.error(str(exc)); results=[]
        if results:
            chosen = st.selectbox("Choose a result", results, format_func=lambda x: f"{x.get('title','Untitled')} ({(x.get('release_date') or '????')[:4]})")
            show_details(chosen)
        else: st.info("No matching movies found.")
    else:
        if demo_mode:
            sections = [("Featured demo movies", DEMO_MOVIES), ("Highly rated", sorted(DEMO_MOVIES,key=lambda m:m["vote_average"],reverse=True)), ("Recent", sorted(DEMO_MOVIES,key=lambda m:m["release_date"],reverse=True))]
        else:
            try:
                with st.spinner("Loading movies from TMDB…"):
                    sections = [("Trending this week", client.trending()), ("Highly rated", client.top_rated()), ("Now playing", client.now_playing())]
            except TMDBError as exc: st.error(str(exc)); sections=[]
        for title, movies in sections: st.subheader(title); grid(movies, title, 6)

elif page == "Recommendations":
    st.title("Recommendations")
    st.caption("Mood is an explicit genre/keyword heuristic—not a classification supplied by TMDB.")
    with st.sidebar:
        st.subheader("Fine-tune")
        selected = st.multiselect("Genres", list(name_to_id), default=[g for g in prefs["favorite_genres"] if g in name_to_id])
        excluded = st.multiselect("Exclude genres", [g for g in name_to_id if g not in selected], default=[g for g in prefs["excluded_genres"] if g in name_to_id and g not in selected])
        mood = st.selectbox("Mood", list(MOOD_MAPPINGS))
        language = st.selectbox("Original language", ["Any", "en", "es", "fr", "ko", "ja", "hi", "de", "it"], index=0)
        min_rating = st.slider("Minimum TMDB rating", 0.0, 9.0, float(prefs["min_rating"]), .5)
        years = st.slider("Release years", 1900, date.today().year, (1980, date.today().year))
        runtimes = st.slider("Runtime (minutes)", 0, 300, (0, 240))
        discovery = st.radio("Discovery style", ["Balanced", "Popular", "Hidden gems"], horizontal=True)
        amount = st.slider("Results", 1, 20, 9)
        omit = st.checkbox("Exclude watched/disliked", True)
    filters = Filters({name_to_id[x] for x in selected}, {name_to_id[x] for x in excluded}, mood, language, min_rating, *years, *runtimes, discovery)
    if demo_mode: catalog = DEMO_MOVIES
    else:
        try:
            with st.spinner("Finding matches…"):
                params = {"sort_by":"popularity.desc", "vote_average.gte":min_rating, "primary_release_date.gte":f"{years[0]}-01-01", "primary_release_date.lte":f"{years[1]}-12-31", "with_runtime.gte":runtimes[0], "with_runtime.lte":runtimes[1]}
                if selected: params["with_genres"] = ",".join(str(name_to_id[x]) for x in selected)
                if excluded: params["without_genres"] = ",".join(str(name_to_id[x]) for x in excluded)
                if language != "Any": params["with_original_language"] = language
                catalog = [hydrate(m) for m in client.discover(**params)]
        except TMDBError as exc: st.error(str(exc)); catalog=[]
    results = recommend(catalog, filters, amount, {name_to_id[x] for x in prefs["favorite_genres"] if x in name_to_id}, db.excluded_ids() if omit else set())
    if st.button("🎲 Surprise me", disabled=not results):
        st.session_state.surprise = random.choice(results)
    if st.session_state.get("surprise") in results:
        st.success("Tonight's pick"); show_details(st.session_state.surprise)
    st.subheader(f"{len(results)} best matches"); grid(results, "rec", amount)

elif page == "Similar Movies":
    st.title("Similar Movies")
    q = st.text_input("Choose a movie you like", placeholder="Start typing a title…")
    if q:
        try: options = [m for m in DEMO_MOVIES if q.lower() in m["title"].lower()] if demo_mode else client.search(q)
        except TMDBError as exc: st.error(str(exc)); options=[]
        if options:
            seed = hydrate(st.selectbox("Movie", options, format_func=lambda x:x.get("title","Untitled")))
            if demo_mode: pool = [m for m in DEMO_MOVIES if m["id"] != seed["id"]]
            else:
                try: pool = [hydrate(m) for m in client.similar(seed["id"])]
                except TMDBError as exc: st.error(str(exc)); pool=[]
            filters = Filters(year_min=1900, year_max=2100, runtime_max=1000)
            grid(recommend(pool, filters, 12, seed=seed), "similar", 12)
        else: st.info("No matching movie found.")

elif page == "Watchlist":
    st.title("Your Watchlist")
    st.caption("Stored only in this local SQLite database; it is not synced between devices.")
    rows = db.get_watchlist()
    if not rows: st.info("Your watchlist is empty. Add a movie from Discover or Recommendations.")
    for row in rows:
        movie = row["metadata"]
        with st.container(border=True):
            c1,c2,c3 = st.columns([3,2,1])
            c1.subheader(row["title"]); c1.caption(f"Status: {row['status'].title()}")
            status = c2.selectbox("Status", ["watchlist","watched","disliked"], index=["watchlist","watched","disliked"].index(row["status"]), key=f"s{row['movie_id']}")
            rating = c2.selectbox("Your rating", [None,1,2,3,4,5], index=([None,1,2,3,4,5].index(row["user_rating"])), key=f"r{row['movie_id']}")
            if c3.button("Save", key=f"u{row['movie_id']}"): db.update_movie(row["movie_id"], status, rating); st.rerun()
            if c3.button("Remove", key=f"d{row['movie_id']}"): db.remove_movie(row["movie_id"]); st.rerun()

else:
    st.title("Settings")
    fav = st.multiselect("Favourite genres", list(name_to_id), default=[g for g in prefs["favorite_genres"] if g in name_to_id])
    exc = st.multiselect("Genres to exclude", [g for g in name_to_id if g not in fav], default=[g for g in prefs["excluded_genres"] if g in name_to_id and g not in fav])
    lang = st.selectbox("Preferred language", ["Any","en","es","fr","ko","ja","hi","de","it"], index=["Any","en","es","fr","ko","ja","hi","de","it"].index(prefs["language"]) if prefs["language"] in ["Any","en","es","fr","ko","ja","hi","de","it"] else 0)
    threshold = st.slider("Default minimum rating", 0.0, 9.0, float(prefs["min_rating"]), .5)
    if st.button("Save preferences", type="primary"): db.save_preferences({"favorite_genres":fav,"excluded_genres":exc,"language":lang,"min_rating":threshold}); st.success("Preferences saved.")
    st.divider(); st.subheader("Local data")
    st.warning("Clearing data permanently removes local preferences and watchlist entries.")
    confirm = st.checkbox("I understand this cannot be undone")
    if st.button("Clear all saved data", disabled=not confirm): db.clear_all(); st.success("Local data cleared."); st.rerun()
    st.subheader("Mood mapping")
    for mood, mapping in MOOD_MAPPINGS.items():
        if mood != "Any": st.write(f"**{mood}:** genres {', '.join(genre_map.get(g,str(g)) for g in mapping['genres'])}; keywords {', '.join(sorted(mapping['keywords']))}")

st.markdown('<div class="attribution">This product uses the TMDB API but is not endorsed or certified by TMDB. Movie metadata and images in live mode are supplied by TMDB. Demo titles and metadata are fictional; no poster artwork is redistributed.</div>', unsafe_allow_html=True)

