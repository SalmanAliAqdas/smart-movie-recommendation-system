import pytest
import responses
from src.tmdb_client import TMDBClient, TMDBAuthError, TMDBError

@responses.activate
def test_search_success_and_credential_header():
    responses.get("https://api.themoviedb.org/3/search/movie", json={"results":[{"id":1,"title":"Film"}]}, status=200)
    client = TMDBClient(read_token="token")
    assert client.search("Film")[0]["id"] == 1
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token"

@responses.activate
def test_genre_map_accepts_language_and_normalizes_response():
    responses.get(
        "https://api.themoviedb.org/3/genre/movie/list",
        json={"genres": [{"id": 28, "name": "Action"}, {"id": 18, "name": " Drama "}]},
        status=200,
    )
    result = TMDBClient(api_key="x").genre_map(language="ur-PK")
    assert result == {28: "Action", 18: "Drama"}
    assert responses.calls[0].request.params["language"] == "ur-PK"

@responses.activate
def test_genres_rejects_invalid_return_shape():
    responses.get("https://api.themoviedb.org/3/genre/movie/list", json={"genres": {}}, status=200)
    with pytest.raises(TMDBError, match="invalid movie genre response"):
        TMDBClient(api_key="x").genre_map()

@responses.activate
def test_homepage_endpoint_forwards_language_page_and_region():
    responses.get("https://api.themoviedb.org/3/movie/now_playing",json={"results":[{"id":9}]},status=200)
    movies=TMDBClient(api_key="x").now_playing(language="ur-PK",page=2,region="PK")
    assert movies==[{"id":9}]
    assert responses.calls[0].request.params["language"]=="ur-PK"
    assert responses.calls[0].request.params["page"]=="2"
    assert responses.calls[0].request.params["region"]=="PK"

@responses.activate
def test_api_auth_failure():
    responses.get("https://api.themoviedb.org/3/movie/popular", json={"status_message":"Invalid"}, status=401)
    with pytest.raises(TMDBAuthError): TMDBClient(api_key="bad").popular()

@responses.activate
def test_invalid_json_failure():
    responses.get("https://api.themoviedb.org/3/movie/popular", body="not json", status=200)
    with pytest.raises(TMDBError): TMDBClient(api_key="x").popular()

@responses.activate
def test_details_parses_cast_director_certification_and_trailer():
    body={"id":1,"genres":[{"id":18,"name":"Drama"}],"credits":{"cast":[{"id":2,"name":"Actor","character":"Hero","profile_path":"/a.jpg"}],"crew":[{"id":3,"name":"Director","job":"Director"}]},"videos":{"results":[{"key":"abc","site":"YouTube","type":"Trailer","official":True}]},"keywords":{"keywords":[{"name":"hope"}]},"release_dates":{"results":[{"iso_3166_1":"US","release_dates":[{"certification":"PG"}]}]}}
    responses.get("https://api.themoviedb.org/3/movie/1", json=body, status=200)
    movie=TMDBClient(api_key="x").details(1)
    assert movie["cast"][0]["character"] == "Hero"
    assert movie["director"]["name"] == "Director"
    assert movie["certification"] == "PG" and movie["trailer"]["key"] == "abc"

