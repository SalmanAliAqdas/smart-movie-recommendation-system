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
def test_api_auth_failure():
    responses.get("https://api.themoviedb.org/3/movie/popular", json={"status_message":"Invalid"}, status=401)
    with pytest.raises(TMDBAuthError): TMDBClient(api_key="bad").popular()

@responses.activate
def test_invalid_json_failure():
    responses.get("https://api.themoviedb.org/3/movie/popular", body="not json", status=200)
    with pytest.raises(TMDBError): TMDBClient(api_key="x").popular()

