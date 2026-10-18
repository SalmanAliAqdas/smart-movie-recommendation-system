"""Exercise the actual homepage with mocked TMDB and an isolated SQLite file."""
from datetime import date
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import src.database as database_module
from src.tmdb_client import TMDBClient, TMDBError

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def homepage(monkeypatch, tmp_path):
    monkeypatch.setenv("TMDB_API_KEY", "app-test-key")
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "")
    monkeypatch.setenv("DEMO_MODE", "false")
    database = database_module.Database
    monkeypatch.setattr(database_module, "Database", lambda _: database(tmp_path / "test.db"))
    calls = []
    status = {"fail":False,"genre_fail":False}

    def get(client, path, **params):
        calls.append((path, params))
        if path == "/genre/movie/list":
            if status["genre_fail"]:
                raise TMDBError("genre service unavailable")
            return {"genres":[{"id":18,"name":"Drama"}]}
        if status["fail"]:
            raise TMDBError("temporary outage")
        if path.startswith("/movie/") and path != "/movie/popular":
            return {"id":int(path.rsplit("/",1)[1]),"title":"Selected movie", "overview":"Existing detail view", "release_date":date.today().isoformat()}
        page = params.get("page",1)
        return {"results":[{"id":(page-1)*20+i,"title":f"Test movie {i}","poster_path":f"/poster{i}.jpg",
                            "release_date":date.today().isoformat(),"vote_average":7.5,"popularity":30} for i in range(1,21)],
                "total_pages":2}

    monkeypatch.setattr(TMDBClient, "_get", get)
    st.cache_data.clear()
    st.cache_resource.clear()
    yield AppTest.from_file(APP, default_timeout=20), calls, status
    st.cache_data.clear()
    st.cache_resource.clear()


def posters(app):
    return "".join(element.proto.body for element in app.get("html"))


def test_homepage_automatically_displays_twenty_posters_and_paginates(homepage):
    app,calls,_ = homepage
    app.run()
    assert not app.exception
    assert posters(app).count('<article class="gallery-card">') == 20
    assert [element.value for element in app.subheader] == ["Explore Movies"]
    assert not app.warning
    assert len([call for call in calls if call[0]=="/discover/movie"]) == 1
    assert not any(call[0].startswith("/movie/") for call in calls)
    app.button(key="gallery-more").click().run()
    assert not app.exception
    assert posters(app).count('<article class="gallery-card">') == 40
    assert not any(button.key == "gallery-more" for button in app.button)
    app.selectbox(key="homepage_sort").select("popular").run()
    assert not app.exception
    assert calls[-1][1]["sort_by"] == "popularity.desc"
    assert posters(app).count('<article class="gallery-card">') == 20


def test_homepage_failure_is_one_compact_message_and_retry_recovers(homepage):
    app,_,status = homepage
    status["fail"] = True
    app.run()
    assert not app.exception and not app.warning
    assert not posters(app)
    assert len([caption for caption in app.caption if "couldn't load" in caption.value]) == 1
    status["fail"] = False
    app.button(key="gallery-retry").click().run()
    assert not app.exception
    assert posters(app).count('<article class="gallery-card">') == 20


def test_load_more_outage_keeps_successful_movie_posters(homepage):
    app,_,status = homepage
    app.run()
    status["fail"] = True
    app.button(key="gallery-more").click().run()
    assert not app.exception and not app.warning
    assert posters(app).count('<article class="gallery-card">') == 20
    assert any("previously loaded" in caption.value for caption in app.caption)


def test_poster_query_opens_existing_movie_details_and_session_selection(homepage):
    app,_,_ = homepage
    app.query_params["gallery_movie"] = "1"
    app.run()
    assert not app.exception
    assert app.session_state["open_movie"]["source"] == "home-gallery"
    assert any(title.value == "Selected movie" for title in app.title)
    assert "gallery_movie" not in app.query_params


def test_genre_service_failure_does_not_block_movie_gallery(homepage):
    app,_,status = homepage
    status["genre_fail"] = True
    app.run()
    assert not app.exception
    assert posters(app).count('<article class="gallery-card">') == 20


def test_no_credentials_shows_setup_message_without_demo_posters(homepage,monkeypatch):
    app,calls,_ = homepage
    monkeypatch.setenv("TMDB_API_KEY", "")
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "")
    app.run()
    assert not app.exception and not posters(app)
    assert any("Connect TMDB" in caption.value for caption in app.caption)
    assert not calls
