from datetime import date
from unittest.mock import Mock

import pytest
import requests
import responses

from src.gallery import GalleryUnavailable, load_gallery_page, merge_movies, select_gallery_movie, usable_movies
from src.gallery_view import gallery_html
from src.tmdb_client import TMDBClient, TMDBError

TODAY = date(2026, 10, 18)


def movie(mid=1, **changes):
    return {"id":mid,"title":f"Movie {mid}","poster_path":f"/poster{mid}.jpg",
            "release_date":"2026-10-01","vote_average":7.2,"vote_count":100,"popularity":20,**changes}


def fake_client():
    client = Mock()
    client.discover_page.return_value = {"results":[movie()],"total_pages":3}
    client.popular.return_value = [movie(2)]
    return client


def test_automatic_recent_discovery_uses_release_bounds_and_votes():
    client = fake_client()
    page = load_gallery_page(client, today=TODAY, language="ur-PK", region="PK")
    assert page.movies == [movie()] and page.has_more
    params = client.discover_page.call_args.kwargs
    assert params["primary_release_date.lte"] == "2026-10-18"
    assert params["primary_release_date.gte"] < "2026-10-01"
    assert params["vote_count.gte"] == 50
    assert params["language"] == "ur-PK" and params["region"] == "PK"
    client.popular.assert_not_called()
    client.details.assert_not_called()


@pytest.mark.parametrize("sort,expected", [("newest","primary_release_date.desc"),("popular","popularity.desc"),("rated","vote_average.desc")])
def test_sort_parameters_and_page_are_forwarded(sort, expected):
    client = fake_client()
    result = load_gallery_page(client, sort=sort, page=3, today=TODAY)
    assert client.discover_page.call_args.args == (3,)
    assert client.discover_page.call_args.kwargs["sort_by"] == expected
    assert result.page == 3 and not result.has_more


def test_invalid_and_future_movies_never_enter_gallery():
    payload = [movie(), movie(), movie(2,poster_path=None), movie(3,title=" "),
               movie(4,release_date="2099-01-01"),movie(5,release_date="invalid"),
               movie(6,poster_path='https://bad.test/image.jpg'),movie(7,adult=True),None]
    assert usable_movies(payload,TODAY) == [movie()]


@pytest.mark.parametrize("first", [{"results":[]}, {"results":"bad"}, None, TMDBError("temporary")])
def test_empty_malformed_and_failed_discovery_use_popular(first):
    client = fake_client()
    if isinstance(first, Exception):
        client.discover_page.side_effect = first
    else:
        client.discover_page.return_value = first
    result = load_gallery_page(client, today=TODAY)
    assert result.source == "popular" and result.movies == [movie(2)]


def test_broad_discovery_recovers_when_first_two_sources_fail():
    client = fake_client()
    client.discover_page.side_effect = [TMDBError("unavailable"),{"results":[movie(3)],"total_pages":1}]
    client.popular.return_value = []
    result = load_gallery_page(client,today=TODAY)
    assert result.source == "broad_discovery"
    assert "primary_release_date.gte" not in client.discover_page.call_args.kwargs
    assert client.discover_page.call_args.kwargs["vote_count.gte"] == 10


def test_all_sources_fail_with_one_retryable_error_and_safe_logs(caplog):
    client = fake_client()
    client.discover_page.side_effect = TMDBError("url?api_key=do-not-log")
    client.popular.side_effect = TMDBError("Bearer do-not-log")
    with pytest.raises(GalleryUnavailable) as error:
        load_gallery_page(client,today=TODAY)
    assert not error.value.auth_failed
    assert "do-not-log" not in caplog.text
    assert "recent_discovery" in caplog.text and "broad_discovery" in caplog.text


@responses.activate
@pytest.mark.parametrize("credentials", [{"read_token":"test-token"},{"api_key":"test-key"}])
def test_gallery_uses_existing_tmdb_authentication(credentials):
    responses.get(TMDBClient.BASE_URL+"/discover/movie",json={"results":[movie()],"total_pages":1})
    load_gallery_page(TMDBClient(**credentials),today=TODAY)
    request = responses.calls[0].request
    if "read_token" in credentials:
        assert request.headers["Authorization"] == "Bearer test-token"
    else:
        assert request.params["api_key"] == "test-key"
    assert request.params["include_adult"] == "false"


@responses.activate
def test_auth_failure_is_explicit_and_does_not_fabricate_or_retry_other_endpoints(caplog):
    responses.get(TMDBClient.BASE_URL+"/discover/movie",json={"status_message":"bad credential"},status=401)
    with pytest.raises(GalleryUnavailable) as error:
        load_gallery_page(TMDBClient(api_key="private-key"),today=TODAY)
    assert error.value.auth_failed and len(responses.calls) == 1
    assert "status=401" in caplog.text and "private-key" not in caplog.text


@responses.activate
def test_transport_error_never_exposes_credential_url(caplog):
    responses.get(TMDBClient.BASE_URL+"/discover/movie",body=requests.ConnectionError("url?api_key=private-key"))
    with pytest.raises(TMDBError) as error:
        TMDBClient(api_key="private-key").discover_page()
    assert "private-key" not in str(error.value) + caplog.text


def test_pagination_merges_unique_movies_in_selected_order():
    merged = merge_movies([movie(1,release_date="2026-09-01"),movie(2)], [movie(2),movie(3,release_date="2026-10-10")],"newest")
    assert [item["id"] for item in merged] == [3,2,1]
    assert [item["id"] for item in merge_movies([], [movie(1,popularity=4),movie(2,popularity=10)],"popular")] == [2,1]
    assert [item["id"] for item in merge_movies([], [movie(1,vote_average=9),movie(2,vote_average=8)],"rated")] == [1,2]


def test_selection_reuses_existing_details_session_shape_and_can_restore_loaded_links():
    assert select_gallery_movie("1",[movie()]) == {"source":"home-gallery","movie":movie()}
    assert select_gallery_movie("20",[]) == {"source":"home-gallery","movie":{"id":20}}
    assert select_gallery_movie("invalid",[]) is None
    assert select_gallery_movie("-1",[]) is None


def test_poster_markup_is_escaped_and_links_to_details():
    html = gallery_html([movie(title='<script>bad</script>')],"rated")
    assert '<script>bad</script>' not in html
    assert '&lt;script&gt;' in html
    assert 'gallery_movie=1' in html and 'gallery_sort=rated' in html
    assert 'https://image.tmdb.org/t/p/w500/poster1.jpg' in html
    assert 'repeat(2,minmax(0,1fr))' in html
