from __future__ import annotations
import os, random
import hashlib
from datetime import date
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.catalog import FAMILY_CERTIFICATIONS, certification_allowed, comparison_winner, filter_movies, is_upcoming, sort_movies
from src.database import Database
from src.demo_data import DEMO_MOVIES, GENRES
from src.i18n import tr
from src.gallery import GalleryUnavailable, SORTS, load_gallery_page, merge_movies, select_gallery_movie, sort_gallery
from src.gallery_view import gallery_html
from src.preferences import merged_preferences
from src.recommender import Filters, MOOD_MAPPINGS, recommend
from src.tmdb_client import TMDBClient, TMDBError
from src.watchlist_export import watchlist_csv

load_dotenv()
st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Nastaliq+Urdu&display=swap');
:root{--ink:#f5f5f7;--muted:#9c9daa;--accent:#ffb547}
.stApp{background:radial-gradient(circle at 85% -10%,#28182f 0,#0d0e13 32%,#090a0e 70%);color:var(--ink)}
.block-container{max-width:1480px;padding:1rem 1.35rem 2rem}
[data-testid="stSidebar"]{background:#0d0e13;border-right:1px solid #ffffff0d}
h1,h2,h3{font-family:'DM Sans',sans-serif;letter-spacing:-.02em}h1{font-size:2rem!important}h2{font-size:1.35rem!important;margin:1.15rem 0 .4rem!important}h3{font-size:.93rem!important;line-height:1.25!important;margin:.35rem 0 .08rem!important}
.catalog-header{display:flex;align-items:center;gap:.65rem;margin:0 0 .55rem}.catalog-mark{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#ffbf5b,#d85065);display:grid;place-items:center}.catalog-title{font-weight:700;font-size:1.08rem}.catalog-subtitle{color:var(--muted);font-size:.76rem}
.section-kicker{color:var(--accent);font-size:.7rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;margin-bottom:-.45rem}
.poster-placeholder{aspect-ratio:2/3;border-radius:10px;background:linear-gradient(145deg,#3c263c,#171827);display:flex;align-items:center;justify-content:center;font-size:2rem}
[data-testid="stImage"] img{aspect-ratio:2/3;object-fit:cover;border-radius:10px;box-shadow:0 10px 28px #0008;transition:transform .18s ease,filter .18s ease}[data-testid="stImage"] img:hover{transform:translateY(-3px);filter:brightness(1.08)}
.meta{color:var(--muted);font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.demo-pill{background:#f6af4518;color:#f6af45;padding:.22rem .55rem;border:1px solid #f6af4530;border-radius:999px;font-size:.7rem}
.stButton>button{border-radius:8px;min-height:1.9rem;padding:.2rem .55rem;font-size:.76rem;border-color:#ffffff17;background:#ffffff08}[data-testid="stVerticalBlockBorderWrapper"]{border-color:#ffffff10!important;background:#11121880!important;border-radius:12px!important}[data-testid="stVerticalBlockBorderWrapper"]>div{padding:.45rem!important}[data-testid="column"]{min-width:0}
div[data-testid="stTextInput"] input{border-radius:10px;background:#15161d;border-color:#ffffff18}.attribution{font-size:.7rem;color:#737480;padding-top:1.25rem}.rtl{direction:rtl;text-align:right;font-family:'Noto Nastaliq Urdu'}
@media(max-width:900px){.block-container{padding:.75rem}.catalog-subtitle{display:none}h2{font-size:1.15rem!important}[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(6)){flex-wrap:wrap}[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(6))>[data-testid="column"]{flex:1 1 calc(25% - 1rem)!important;min-width:calc(25% - 1rem)!important}}
@media(max-width:600px){[data-testid="stHorizontalBlock"]:has(>[data-testid="column"]:nth-child(6))>[data-testid="column"]{flex-basis:calc(50% - .5rem)!important;min-width:calc(50% - .5rem)!important}}
</style>""",unsafe_allow_html=True)

def secret(name):
    try:return st.secrets.get(name) or os.getenv(name)
    except Exception:return os.getenv(name)

token,key=secret("TMDB_READ_ACCESS_TOKEN"),secret("TMDB_API_KEY")
demo_mode=str(secret("DEMO_MODE") or "").lower()=="true" or not(token or key)
db=Database(Path(__file__).with_name("movie_recommender.db")); prefs=merged_preferences(db.get_preferences())
ui=prefs.get("interface_language","en"); tmdb_lang="ur-PK" if ui=="ur" else "en-US"
TMDB_CLIENT_CACHE_VERSION = hashlib.sha256(Path(__file__).with_name("src").joinpath("tmdb_client.py").read_bytes()).hexdigest()
@st.cache_resource
def get_v2_client(k,t,cache_version):
    # Source fingerprint invalidates retained clients whenever their methods change.
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
GALLERY_CACHE_VERSION = hashlib.sha256(Path(__file__).with_name("src").joinpath("gallery.py").read_bytes()).hexdigest()
credential_identity = hashlib.sha256(((key or "") + "\0" + (token or "")).encode()).hexdigest()
@st.cache_data(ttl=600,max_entries=128,show_spinner=False)
def live_gallery(sort,page,lang,region,day,identity,client_version,gallery_version,attempt,_client):
    # Only successful pages are cached; exceptions remain retryable.
    return load_gallery_page(_client,sort,page,lang,region,date.fromisoformat(day))

genre_error = False
try:genre_map=GENRES if demo_mode else live_genres(tmdb_lang)
except TMDBError:
    # A genre-service outage must not prevent the independent poster gallery.
    genre_map=GENRES;genre_error=True
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
    year=release[:4] if release != "Unknown" else "—"
    rt=f" · ★ {rating:.1f}" if isinstance(rating,(int,float)) else ""
    st.markdown(f'<div class="meta">{year}{rt}{" · Upcoming" if upcoming else ""}</div>',unsafe_allow_html=True)
    if m.get("reasons"):st.caption("Why: "+"; ".join(m["reasons"][:2])+".")
    if st.button(tr("view_details",ui),key=f"open-{k}",use_container_width=True):
        st.session_state.open_movie={"source":k.rsplit("-",2)[0],"movie":m}
    add_button(m,k)
def grid(movies,prefix,count=12,upcoming=False):
    if not movies:st.info(tr("no_results",ui));return
    cols=st.columns(min(6,len(movies)),gap="small")
    for i,m in enumerate(movies[:count]):
        with cols[i%len(cols)]:
            with st.container(border=True):card(m,f"{prefix}-{m.get('id')}-{i}",upcoming)
    opened=st.session_state.get("open_movie")
    if opened and opened.get("source")==prefix:
        with st.container(border=True):details(opened["movie"])
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
    st.markdown('<div class="catalog-header"><div class="catalog-mark">▶</div><div><div class="catalog-title">CineMatch</div><div class="catalog-subtitle">Discover your next great watch</div></div></div>',unsafe_allow_html=True)
    q=st.text_input(tr("search",ui),placeholder="Search movies by title…",label_visibility="collapsed")
    if q.strip():
        try:results=[x for x in DEMO_MOVIES if q.lower() in x["title"].lower()] if demo_mode else client.search(q,1,tmdb_lang)
        except TMDBError as exc:st.error(str(exc));results=[]
        if results:details(st.selectbox(tr("details",ui),results,format_func=lambda x:f"{x.get('title')} ({(x.get('release_date') or '????')[:4]})"))
        else:st.info(tr("no_results",ui))
    heading,sort_control=st.columns([3,1],vertical_alignment="center")
    heading.subheader(tr("explore_movies",ui))
    initial_sort=st.query_params.get("gallery_sort","newest")
    initial_sort=initial_sort if initial_sort in SORTS else "newest"
    gallery_sort=sort_control.selectbox(tr("sort",ui),list(SORTS),index=list(SORTS).index(initial_sort),format_func=lambda x:tr("gallery_sort_"+x,ui),key="homepage_sort",label_visibility="collapsed")
    day=date.today().isoformat()
    snapshot_key=(gallery_sort,tmdb_lang,"US",day,credential_identity,TMDB_CLIENT_CACHE_VERSION,GALLERY_CACHE_VERSION)
    snapshots=st.session_state.setdefault("gallery_snapshots",{})
    gallery=snapshots.setdefault(snapshot_key,{"movies":[],"page":0,"has_more":False,"request":1,"attempt":0,"error":None})
    requested=gallery.pop("request",None)
    if requested is not None:
        if client is None:
            gallery["error"]=tr("gallery_config",ui)
        else:
            try:
                with st.spinner(tr("gallery_loading",ui)):
                    result=live_gallery(gallery_sort,requested,tmdb_lang,"US",day,credential_identity,TMDB_CLIENT_CACHE_VERSION,GALLERY_CACHE_VERSION,gallery["attempt"],client)
                gallery["movies"]=merge_movies(gallery["movies"],result.movies,gallery_sort)
                gallery.update(page=requested,has_more=result.has_more,error=None)
            except GalleryUnavailable as exc:
                gallery["error"]=tr("gallery_auth" if exc.auth_failed else "gallery_unavailable",ui)
                gallery["failed_page"]=requested
                # Keep previously successful real metadata during a temporary outage.
                if not gallery["movies"]:
                    for saved_key,saved in snapshots.items():
                        if saved_key[1:]==snapshot_key[1:] and saved["movies"]:
                            gallery["movies"]=sort_gallery(saved["movies"],gallery_sort);break
    if gallery["movies"]:
        st.html(gallery_html(gallery["movies"],gallery_sort,language=ui))
    if gallery["error"]:
        st.caption(gallery["error"]+(" "+tr("gallery_cached",ui) if gallery["movies"] else ""))
        if st.button(tr("gallery_retry",ui),key="gallery-retry"):
            gallery["attempt"]+=1;gallery["request"]=gallery.get("failed_page",1);st.rerun()
    elif gallery["has_more"]:
        if st.button(tr("load_more",ui),key="gallery-more",use_container_width=True):
            gallery["request"]=gallery["page"]+1;st.rerun()
    selected=st.query_params.get("gallery_movie")
    if selected is not None:
        opened=select_gallery_movie(selected,gallery["movies"])
        del st.query_params["gallery_movie"]
        if opened and client:
            st.session_state.open_movie=opened
            @st.dialog(tr("details",ui),width="large")
            def gallery_details():
                details(st.session_state.open_movie["movie"])
            gallery_details()
    with st.expander(tr("advanced_discovery",ui),expanded=False):
        if genre_error:st.caption(tr("gallery_genres",ui))
        with st.form("advanced"):
            a,b,c=st.columns(3);gs=a.multiselect("Genres",list(name_to_id));ex=a.multiselect("Exclude genres",[x for x in name_to_id if x not in gs]);years=b.slider("Release years",1900,date.today().year,(1980,date.today().year));lang=b.selectbox("Original language",["Any","en","ur","hi","ko","ja","es","fr","de"]);rating=c.slider("Minimum TMDB rating",0.,9.,0.,.5);votes=c.number_input("Minimum vote count",0,1000000,0,100);runtime=a.slider("Runtime where available",0,300,(0,240));country=b.selectbox("Country of origin",["Any","US","GB","PK","IN","KR","JP","FR","DE","CA","AU"]);sort=c.selectbox(tr("sort",ui),["Popularity","Newest release","Oldest release","Highest rated","Most votes"]);family=a.checkbox("Family-Friendly mode");region=b.selectbox("Certification region",["US","GB","PK","IN","CA","AU"]);certs=c.multiselect("Allowed certifications",sorted(FAMILY_CERTIFICATIONS[region]),default=sorted(FAMILY_CERTIFICATIONS[region])) if family else [];submitted=st.form_submit_button("Discover movies",type="primary")
        if submitted:st.session_state.discovery_page=1;st.session_state.discovery_active=True
        if "discovery_page" not in st.session_state:st.session_state.discovery_page=1
        if st.session_state.get("discovery_active"):
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
