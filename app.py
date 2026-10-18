from __future__ import annotations
import os, random
from datetime import date
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.catalog import FAMILY_CERTIFICATIONS, certification_allowed, comparison_winner, filter_movies, is_upcoming, sort_movies
from src.database import Database
from src.demo_data import DEMO_MOVIES, GENRES
from src.i18n import tr
from src.homepage import load_homepage_sections
from src.preferences import merged_preferences
from src.recommender import Filters, MOOD_MAPPINGS, recommend
from src.tmdb_client import TMDBClient, TMDBError
from src.watchlist_export import watchlist_csv

load_dotenv()
st.set_page_config(page_title="CineMatch 2.0", page_icon="🎬", layout="wide")
st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Noto+Nastaliq+Urdu&family=Playfair+Display:wght@700&display=swap');.stApp{background:radial-gradient(circle at 80% 0%,#2b1539 0,#0c0d13 34%,#08090d 100%);color:#f4f1eb}.block-container{max-width:1400px;padding-top:2rem}.hero{padding:2.7rem;border:1px solid #ffffff1a;border-radius:24px;background:linear-gradient(120deg,#171824ee,#38152dcc);margin-bottom:1.4rem}.hero h1{font-family:'Playfair Display';font-size:3.35rem;margin:0}.eyebrow{color:#f6af45;letter-spacing:.18em;font-weight:700;font-size:.78rem}.poster-placeholder{height:190px;border-radius:12px;background:linear-gradient(145deg,#542343,#171827);display:flex;align-items:center;justify-content:center;font-size:3rem}.meta{color:#aaa9b4;font-size:.84rem}.demo-pill{background:#f6af4520;color:#f6af45;padding:.25rem .6rem;border-radius:999px;font-size:.75rem}.stButton>button{border-radius:999px}.attribution{font-size:.78rem;color:#8d8d99;padding-top:2rem}.rtl{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu'}h1,h2,h3{font-family:'DM Sans'}</style>""",unsafe_allow_html=True)

def secret(name):
    try:return st.secrets.get(name) or os.getenv(name)
    except Exception:return os.getenv(name)

token,key=secret("TMDB_READ_ACCESS_TOKEN"),secret("TMDB_API_KEY")
demo_mode=str(secret("DEMO_MODE") or "").lower()=="true" or not(token or key)
db=Database(Path(__file__).with_name("movie_recommender.db")); prefs=merged_preferences(db.get_preferences())
ui=prefs.get("interface_language","en"); tmdb_lang="ur-PK" if ui=="ur" else "en-US"
TMDB_CLIENT_CACHE_VERSION = 2
@st.cache_resource
def get_v2_client(k,t,cache_version):
    # cache_version intentionally invalidates pre-V2 TMDBClient instances after hot reloads.
    return TMDBClient(api_key=k,read_token=t)
client=None if demo_mode else get_v2_client(key,token,TMDB_CLIENT_CACHE_VERSION)
@st.cache_data(ttl=3600,show_spinner=False)
def live_genres(lang):return client.genre_map(language=lang)
@st.cache_data(ttl=1800,show_spinner=False)
def live_details(mid,lang,region):return client.details(mid,lang,region)
@st.cache_data(ttl=1800,show_spinner=False)
def live_person(pid,lang):return client.person_movie_credits(pid,lang)
@st.cache_data(ttl=3600,show_spinner=False)
def live_collection(cid,lang):return client.collection(cid,lang)
@st.cache_data(ttl=900,show_spinner=False)
def live_homepage(lang,region):return load_homepage_sections(client,lang,region)

try:genre_map=GENRES if demo_mode else live_genres(tmdb_lang)
except TMDBError as exc:st.error(str(exc));st.stop()
name_to_id={v:k for k,v in genre_map.items()}
def hydrate(m,region="US"):
    if demo_mode:return m
    try:return live_details(int(m["id"]),tmdb_lang,region)
    except TMDBError:return m
def poster(m,profile=False):
    path=m.get("profile_path") if profile else m.get("poster_path")
    if path and client:st.image(client.profile_url(path) if profile else client.poster_url(path),use_container_width=True)
    else:st.markdown('<div class="poster-placeholder">👤</div>' if profile else '<div class="poster-placeholder">🎞️</div>',unsafe_allow_html=True)
def add_button(m,k):
    if st.button(tr("watchlist_add",ui),key=k,use_container_width=True):db.add_movie(m);st.toast(f"Added {m.get('title','movie')}")
def card(m,k,upcoming=False):
    poster(m);rating=m.get("vote_average"); release=m.get("release_date") or "Unknown"
    st.markdown(f"### {m.get('title') or 'Untitled'}")
    rt=f" · TMDB ⭐ {rating:.1f} ({int(m.get('vote_count') or 0):,})" if isinstance(rating,(int,float)) else ""
    st.markdown(f'<div class="meta">{release[:10]} · {m.get("original_language","—").upper()}{rt}{" · UPCOMING" if upcoming else ""}</div>',unsafe_allow_html=True)
    if m.get("reasons"):st.caption("Why: "+"; ".join(m["reasons"][:2])+".")
    if st.button(tr("view_details",ui),key=f"open-{k}",use_container_width=True):
        st.session_state.open_movie={"source":k.rsplit("-",2)[0],"movie":m}
    add_button(m,k)
def grid(movies,prefix,count=12,upcoming=False):
    if not movies:st.info(tr("no_results",ui));return
    cols=st.columns(min(3,len(movies)))
    for i,m in enumerate(movies[:count]):
        with cols[i%len(cols)]:
            with st.container(border=True):card(m,f"{prefix}-{m.get('id')}-{i}",upcoming)
    opened=st.session_state.get("open_movie")
    if opened and opened.get("source")==prefix:
        with st.container(border=True):details(opened["movie"])
def movie_shelf(title,movies,prefix,upcoming=False,error=None):
    st.subheader(title)
    if error:
        st.warning(tr("homepage_error",ui));return
    if not movies:
        st.info(tr("no_results",ui));return
    state_key=f"shelf_count_{prefix}";visible=st.session_state.get(state_key,6)
    grid(movies,prefix,min(visible,len(movies)),upcoming)
    if len(movies)>6:
        left,right=st.columns([1,5])
        if visible<len(movies) and left.button(tr("view_more",ui),key=f"more-{prefix}"):
            st.session_state[state_key]=min(visible+6,len(movies));st.rerun()
        if visible>6 and right.button(tr("show_less",ui),key=f"less-{prefix}"):
            st.session_state[state_key]=6;st.rerun()
def people(m):
    persons=[]; director=m.get("director")
    if isinstance(director,dict):persons.append({**director,"role":"Director"})
    persons += [{**x,"role":x.get("character") or "Cast"} for x in (m.get("cast") or []) if isinstance(x,dict)]
    if not persons:return
    st.subheader("Cast & crew");cols=st.columns(min(4,len(persons)))
    for i,p in enumerate(persons):
        with cols[i%len(cols)]:poster(p,True);st.write(f"**{p.get('name','Unknown')}**");st.caption(p["role"])
    p=st.selectbox("Explore this person's movies",[None]+persons,format_func=lambda x:"Select an actor or director" if x is None else f"{x['name']} — {x['role']}",key=f"person-{m['id']}")
    if p and p.get("id") and client:grid(sort_movies(live_person(p["id"],tmdb_lang),"Newest release"),f"person-{p['id']}",6)
def details(m,region="US",full=True):
    m=hydrate(m,region);a,b=st.columns([1,2])
    with a:poster(m);add_button(m,f"detail-{m['id']}")
    with b:
        st.title(m.get("title") or "Untitled"); gs=m.get("genres") or []
        if gs and isinstance(gs[0],dict):gs=[x.get("name","") for x in gs]
        st.write(" · ".join(filter(None,[(m.get("release_date") or "")[:4],", ".join(gs),f"{m.get('runtime')} min" if m.get("runtime") else None,(m.get("original_language") or "").upper()])))
        st.write(f"TMDB ⭐ {float(m.get('vote_average') or 0):.1f} · {int(m.get('vote_count') or 0):,} user votes · Popularity {float(m.get('popularity') or 0):.1f}")
        st.write(f"**{region} certification:** {m['certification']}" if m.get("certification") else f"No {region} certification is available from TMDB.")
        st.write(m.get("overview") or "No synopsis is available in the selected language.")
        d=m.get("director");dn=d.get("name") if isinstance(d,dict) else d
        if dn:st.write("**Director:**",dn)
        st.markdown(f"[View on TMDB](https://www.themoviedb.org/movie/{m['id']})")
    if full:
        v=m.get("trailer")
        if v:st.subheader(f"{v.get('type','Trailer')} · {'Official' if v.get('official') else 'TMDB-listed'}");st.video(f"https://www.youtube.com/watch?v={v['key']}",autoplay=False)
        elif m.get("trailer_url"):st.markdown(f"[Trailer]({m['trailer_url']})")
        else:st.info("No trailer or teaser is currently listed by TMDB.")
        people(m)
        if m.get("belongs_to_collection"):st.info(f"Part of **{m['belongs_to_collection'].get('name')}**. Explore it in Collections.")
    return m

with st.sidebar:
    st.markdown("## 🎬 CineMatch 2.0");st.caption("Your next great watch, explained.")
    groups={"Explore":["Discover","Recommendations","Similar Movies","Upcoming"],"Deep dive":["Compare","Collections"],"Personal":["Watchlist","Settings"]}
    group=st.selectbox("Section",list(groups),label_visibility="collapsed");page=st.radio("Navigate",groups[group],format_func=lambda x:tr(x,ui),label_visibility="collapsed")
    st.divider();st.markdown('<span class="demo-pill">DEMO CATALOG</span>' if demo_mode else '<span class="demo-pill">LIVE TMDB</span>',unsafe_allow_html=True)
if ui=="ur":st.markdown('<div class="rtl">اردو انٹرفیس فعال ہے۔ دستیاب نہ ہونے پر فلمی معلومات انگریزی میں دکھائی جاتی ہیں۔</div>',unsafe_allow_html=True)

if page=="Discover":
    st.markdown('<section class="hero"><div class="eyebrow">CINEMATCH 2.0</div><h1>Find a story worth staying up for.</h1><p>Title search and advanced discovery are separate, so every filter does what it says.</p></section>',unsafe_allow_html=True)
    with st.container():
        st.subheader(tr("title_search",ui))
        q=st.text_input(tr("search",ui));p=st.number_input("Results page",1,500,1)
        if q.strip():
            try:results=[x for x in DEMO_MOVIES if q.lower() in x["title"].lower()] if demo_mode else client.search(q,int(p),tmdb_lang)
            except TMDBError as exc:st.error(str(exc));results=[]
            if results:details(st.selectbox(tr("details",ui),results,format_func=lambda x:f"{x.get('title')} ({(x.get('release_date') or '????')[:4]})"))
            else:st.info(tr("no_results",ui))
    with st.spinner("Loading movies from TMDB…"):
        if demo_mode:
            home={"trending":DEMO_MOVIES,"popular":sorted(DEMO_MOVIES,key=lambda x:x.get("popularity",0),reverse=True),"top_rated":sorted(DEMO_MOVIES,key=lambda x:x.get("vote_average",0),reverse=True),"now_playing":sorted(DEMO_MOVIES,key=lambda x:x.get("release_date","") ,reverse=True),"upcoming":[]};home_errors={}
        else:
            home,home_errors=live_homepage(tmdb_lang,"US")
    movie_shelf(tr("trending_week",ui),home["trending"],"home-trending",error=home_errors.get("trending"))
    movie_shelf(tr("popular_movies",ui),home["popular"],"home-popular",error=home_errors.get("popular"))
    movie_shelf(tr("top_rated_movies",ui),home["top_rated"],"home-top",error=home_errors.get("top_rated"))
    movie_shelf(tr("now_playing",ui),home["now_playing"],"home-now",error=home_errors.get("now_playing"))
    movie_shelf(tr("upcoming_movies",ui),home["upcoming"],"home-upcoming",True,home_errors.get("upcoming"))
    st.subheader(tr("browse_genre",ui))
    browse_genre=st.selectbox(tr("browse_genre",ui),["—"]+list(name_to_id),label_visibility="collapsed")
    if browse_genre!="—":
        try:
            genre_movies=[m for m in DEMO_MOVIES if name_to_id[browse_genre] in m.get("genre_ids",[])] if demo_mode else client.discover(with_genres=str(name_to_id[browse_genre]),sort_by="popularity.desc",language=tmdb_lang)
            movie_shelf(browse_genre,genre_movies,"home-genre")
        except TMDBError:
            st.warning(tr("homepage_error",ui))
    with st.expander(tr("advanced_discovery",ui),expanded=False):
        with st.form("advanced"):
            a,b,c=st.columns(3);gs=a.multiselect("Genres",list(name_to_id));ex=a.multiselect("Exclude genres",[x for x in name_to_id if x not in gs]);years=b.slider("Release years",1900,date.today().year,(1980,date.today().year));lang=b.selectbox("Original language",["Any","en","ur","hi","ko","ja","es","fr","de"]);rating=c.slider("Minimum TMDB rating",0.,9.,0.,.5);votes=c.number_input("Minimum vote count",0,1000000,0,100);runtime=a.slider("Runtime where available",0,300,(0,240));country=b.selectbox("Country of origin",["Any","US","GB","PK","IN","KR","JP","FR","DE","CA","AU"]);sort=c.selectbox(tr("sort",ui),["Popularity","Newest release","Oldest release","Highest rated","Most votes"]);family=a.checkbox("Family-Friendly mode");region=b.selectbox("Certification region",["US","GB","PK","IN","CA","AU"]);certs=c.multiselect("Allowed certifications",sorted(FAMILY_CERTIFICATIONS[region]),default=sorted(FAMILY_CERTIFICATIONS[region])) if family else [];submitted=st.form_submit_button("Discover movies",type="primary")
        if submitted:st.session_state.discovery_page=1
        if "discovery_page" not in st.session_state:st.session_state.discovery_page=1
        try:
            if demo_mode:catalog=DEMO_MOVIES
            else:
                params={"sort_by":{"Popularity":"popularity.desc","Newest release":"primary_release_date.desc","Oldest release":"primary_release_date.asc","Highest rated":"vote_average.desc","Most votes":"vote_count.desc"}[sort],"vote_average.gte":rating,"vote_count.gte":votes,"primary_release_date.gte":f"{years[0]}-01-01","primary_release_date.lte":f"{years[1]}-12-31","with_runtime.gte":runtime[0],"with_runtime.lte":runtime[1],"language":tmdb_lang}
                if gs:params["with_genres"]=",".join(str(name_to_id[x]) for x in gs)
                if ex:params["without_genres"]=",".join(str(name_to_id[x]) for x in ex)
                if lang!="Any":params["with_original_language"]=lang
                if country!="Any":params["with_origin_country"]=country
                catalog=client.discover(st.session_state.discovery_page,**params);catalog=[hydrate(x,region) for x in catalog] if family or country!="Any" or runtime!=(0,240) else catalog
            catalog=filter_movies(catalog,genres={name_to_id[x] for x in gs},excluded={name_to_id[x] for x in ex},year_min=years[0],year_max=years[1],language=lang,rating=rating,votes=votes,runtime_min=runtime[0],runtime_max=runtime[1],country=country)
            if family:catalog=[x for x in catalog if certification_allowed(x.get("certification"),region,True,set(certs))]
            grid(sort_movies(catalog,sort),f"discovery-{st.session_state.discovery_page}")
            if not demo_mode and st.button(tr("load_more",ui)):st.session_state.discovery_page+=1;st.rerun()
        except TMDBError as exc:st.error(str(exc))
        if family:st.warning("Certifications vary by region. Unclassified titles are excluded; parents or guardians should verify suitability independently.")

elif page=="Recommendations":
    st.title(tr("Recommendations",ui));st.caption("Mood is an explicit genre/keyword heuristic—not a TMDB classification.")
    with st.form("recommend"):
        a,b,c=st.columns(3);gs=a.multiselect("Genres",list(name_to_id),default=[x for x in prefs["favorite_genres"] if x in name_to_id]);ex=a.multiselect("Exclude genres",[x for x in name_to_id if x not in gs],default=[x for x in prefs["excluded_genres"] if x in name_to_id and x not in gs]);mood=b.selectbox("Mood",list(MOOD_MAPPINGS));lang=b.selectbox("Original language",["Any","en","ur","hi","ko","ja","es","fr"]);rating=b.slider("Minimum TMDB rating",0.,9.,float(prefs["min_rating"]),.5);years=c.slider("Release years",1900,date.today().year,(1980,date.today().year));runtime=c.slider("Runtime",0,300,(0,240));style=c.radio("Discovery style",["Balanced","Popular","Hidden gems"],horizontal=True);family=a.checkbox("Family-Friendly mode");region=b.selectbox("Certification region",["US","GB","PK","IN","CA","AU"],key="rec-region");amount=c.slider("Results",1,20,9);st.form_submit_button("Recommend",type="primary")
    f=Filters({name_to_id[x] for x in gs},{name_to_id[x] for x in ex},mood,lang,rating,*years,*runtime,style)
    try:
        if demo_mode:catalog=DEMO_MOVIES
        else:
            params={"sort_by":"popularity.desc","vote_average.gte":rating,"primary_release_date.gte":f"{years[0]}-01-01","primary_release_date.lte":f"{years[1]}-12-31","with_runtime.gte":runtime[0],"with_runtime.lte":runtime[1],"language":tmdb_lang}
            if gs:params["with_genres"]=",".join(str(name_to_id[x]) for x in gs)
            if ex:params["without_genres"]=",".join(str(name_to_id[x]) for x in ex)
            if lang!="Any":params["with_original_language"]=lang
            catalog=[hydrate(x,region) for x in client.discover(**params)]
        if family:catalog=[x for x in catalog if certification_allowed(x.get("certification"),region,True)]
        results=recommend(catalog,f,amount,{name_to_id[x] for x in prefs["favorite_genres"] if x in name_to_id},db.excluded_ids())
        if st.button("🎲 Surprise me",disabled=not results):st.session_state.surprise=random.choice(results)
        if st.session_state.get("surprise") in results:details(st.session_state.surprise,region)
        grid(results,"rec",amount)
    except TMDBError as exc:st.error(str(exc))

elif page=="Similar Movies":
    st.title(tr("Similar Movies",ui));q=st.text_input("Choose a movie you like")
    if q:
        try:opts=[x for x in DEMO_MOVIES if q.lower() in x["title"].lower()] if demo_mode else client.search(q,language=tmdb_lang)
        except TMDBError as exc:st.error(str(exc));opts=[]
        if opts:
            seed=hydrate(st.selectbox("Movie",opts,format_func=lambda x:x.get("title")));pool=[x for x in DEMO_MOVIES if x["id"]!=seed["id"]] if demo_mode else [hydrate(x) for x in client.similar(seed["id"])]
            grid(recommend(pool,Filters(year_min=1900,year_max=2100,runtime_max=1000),12,seed=seed),"similar")

elif page=="Upcoming":
    st.title(tr("Upcoming",ui));st.info("Release dates may change. No cinema or streaming availability is implied.")
    a,b,c=st.columns(3);region=a.selectbox("Release region",["US","GB","PK","IN","CA","AU"]);genre=b.selectbox("Genre",["Any"]+list(name_to_id));lang=c.selectbox("Original language",["Any","en","ur","hi","ko","ja","es","fr"],key="up-lang");order=st.radio("Release order",["Soonest first","Latest first"],horizontal=True)
    try:
        ms=[x for x in DEMO_MOVIES if is_upcoming(x)] if demo_mode else client.upcoming(language=tmdb_lang,region=region).get("results",[]);ms=filter_movies(ms,genres=set() if genre=="Any" else {name_to_id[genre]},language=lang,year_min=date.today().year,year_max=date.today().year+5);ms=sorted(ms,key=lambda x:x.get("release_date") or "9999",reverse=order=="Latest first");grid(ms,"upcoming",12,True)
        if ms:
            selected_upcoming=st.selectbox("Open upcoming movie details and trailer",ms,format_func=lambda x:f"{x.get('title','Untitled')} — {x.get('release_date','Unknown')}")
            details(selected_upcoming,region)
    except TMDBError as exc:st.error(str(exc))

elif page=="Compare":
    st.title(tr("Compare",ui));a,b=st.columns(2);qa=a.text_input("First movie");qb=b.text_input("Second movie")
    try:
        oa=([x for x in DEMO_MOVIES if qa.lower() in x["title"].lower()] if demo_mode else client.search(qa,language=tmdb_lang)) if qa else [];ob=([x for x in DEMO_MOVIES if qb.lower() in x["title"].lower()] if demo_mode else client.search(qb,language=tmdb_lang)) if qb else []
        if oa and ob:
            x=a.selectbox("Select first",oa,format_func=lambda z:z.get("title"));y=b.selectbox("Select second",ob,format_func=lambda z:z.get("title"))
            if x["id"]==y["id"]:st.warning("Choose two different movies.")
            else:
                l,r=st.columns(2)
                with l:ld=details(x,full=False)
                with r:rd=details(y,full=False)
                winner=comparison_winner(ld,rd);st.info((f"{winner} has the higher TMDB user rating. " if winner else "The ratings are tied. ")+"Ratings are user-generated and depend on vote counts; this is not an objective judgment of quality.")
    except TMDBError as exc:st.error(str(exc))

elif page=="Collections":
    st.title(tr("Collections",ui));q=st.text_input("Search for a movie in a franchise")
    if q:
        try:opts=[x for x in DEMO_MOVIES if q.lower() in x["title"].lower()] if demo_mode else client.search(q,language=tmdb_lang)
        except TMDBError as exc:st.error(str(exc));opts=[]
        if opts:
            m=hydrate(st.selectbox("Movie",opts,format_func=lambda x:x.get("title")));col=m.get("belongs_to_collection")
            if col and client:
                data=live_collection(col["id"],tmdb_lang);st.subheader(data.get("name"));parts=sorted(data.get("parts",[]),key=lambda x:x.get("release_date") or "9999");grid(parts,"collection",30)
                if parts:details(st.selectbox("Open a collection movie",parts,format_func=lambda x:f"{x.get('title','Untitled')} ({(x.get('release_date') or '????')[:4]})",key="collection-part"))
            else:st.info("TMDB does not list this movie in an official collection. Similar movies are not treated as franchise entries.")

elif page=="Watchlist":
    st.title(tr("Watchlist",ui));st.warning("This app has one shared local SQLite file and no authentication. On a public deployment, entries may be visible to others and local storage may reset.")
    rows=db.get_watchlist();st.download_button("Export watchlist as CSV",watchlist_csv(rows),"cinematch-watchlist.csv","text/csv",disabled=not rows)
    if not rows:st.info("Your watchlist is empty.")
    for row in rows:
        with st.container(border=True):
            a,b,c=st.columns([3,2,1]);a.subheader(row["title"]);a.caption(f"Status: {row['status'].title()} · Added: {row.get('created_at') or 'Unknown'}");status=b.selectbox("Status",["watchlist","watched","disliked"],index=["watchlist","watched","disliked"].index(row["status"]),key=f"s{row['movie_id']}");rating=b.selectbox("Your rating",[None,1,2,3,4,5],index=[None,1,2,3,4,5].index(row["user_rating"]),key=f"r{row['movie_id']}")
            if c.button("Save",key=f"u{row['movie_id']}"):db.update_movie(row["movie_id"],status,rating);st.rerun()
            if c.button("Remove",key=f"d{row['movie_id']}"):db.remove_movie(row["movie_id"]);st.rerun()

else:
    st.title(tr("Settings",ui));interface=st.selectbox(tr("language",ui),["English","اردو"],index=1 if ui=="ur" else 0);fav=st.multiselect("Favourite genres",list(name_to_id),default=[x for x in prefs["favorite_genres"] if x in name_to_id]);ex=st.multiselect("Genres to exclude",[x for x in name_to_id if x not in fav],default=[x for x in prefs["excluded_genres"] if x in name_to_id and x not in fav]);langs=["Any","en","ur","hi","ko","ja","es","fr"];lang=st.selectbox("Preferred movie language",langs,index=langs.index(prefs["language"]) if prefs["language"] in langs else 0);rating=st.slider("Default minimum TMDB rating",0.,9.,float(prefs["min_rating"]),.5)
    if st.button("Save preferences",type="primary"):db.save_preferences({"favorite_genres":fav,"excluded_genres":ex,"language":lang,"min_rating":rating,"interface_language":"ur" if interface=="اردو" else "en"});st.success(tr("saved",ui));st.rerun()
    st.divider();st.subheader("Mood mappings")
    for mood,m in MOOD_MAPPINGS.items():
        if mood!="Any":st.write(f"**{mood}:** genres {', '.join(genre_map.get(g,str(g)) for g in m['genres'])}; keywords {', '.join(sorted(m['keywords']))}")
    st.subheader("Local data");st.warning("Clearing permanently removes local preferences and watchlist entries.");confirm=st.checkbox("I understand this cannot be undone")
    if st.button("Clear all saved data",disabled=not confirm):db.clear_all();st.rerun()

st.markdown('<div class="attribution">This product uses the TMDB API but is not endorsed or certified by TMDB. Live metadata and images are supplied by TMDB. Demo titles are fictional; no poster or trailer media is redistributed.</div>',unsafe_allow_html=True)
