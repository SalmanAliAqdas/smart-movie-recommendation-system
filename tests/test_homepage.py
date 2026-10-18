from datetime import date

from src.homepage import SECTION_KEYS, complete_homepage_sections, load_homepage_sections, released_newest_first

class FakeClient:
    def __init__(self, fail=None): self.fail=fail; self.calls=[]
    def _result(self,name,**kwargs):
        self.calls.append((name,kwargs))
        if self.fail==name: raise RuntimeError("temporary failure")
        return {"results":[{"id":len(self.calls),"title":name}] } if name=="upcoming" else [{"id":len(self.calls),"title":name}]
    def trending(self,**kwargs): return self._result("trending",**kwargs)
    def popular(self,**kwargs): return self._result("popular",**kwargs)
    def top_rated(self,**kwargs): return self._result("top_rated",**kwargs)
    def now_playing(self,**kwargs):
        self.calls.append(("now_playing",kwargs))
        return [{"id":10,"title":"newest","release_date":"2025-03-02"},{"id":11,"title":"older","release_date":"2025-01-01"}]
    def upcoming(self,**kwargs): return self._result("upcoming",**kwargs)

def test_default_homepage_loads_every_movie_section():
    client=FakeClient()
    sections,errors=load_homepage_sections(client,"ur-PK","PK")
    assert tuple(sections)==SECTION_KEYS
    assert all(sections[key] for key in SECTION_KEYS)
    assert errors=={}
    assert all(call[1]["language"]=="ur-PK" for call in client.calls)
    assert dict(client.calls)["now_playing"]["region"]=="PK"
    assert dict(client.calls)["upcoming"]["region"]=="PK"

def test_latest_movies_are_released_and_sorted_newest_first():
    movies=[
        {"id":1,"release_date":"2025-01-01"},
        {"id":2,"release_date":"2025-03-01"},
        {"id":3,"release_date":"2025-04-01"},
        {"id":4,"release_date":""},
    ]
    result=released_newest_first(movies,date(2025,3,15))
    assert [movie["id"] for movie in result]==[2,1]

def test_homepage_endpoint_failure_is_isolated():
    sections,errors=load_homepage_sections(FakeClient(fail="popular"))
    assert sections["popular"]==[]
    assert "popular" in errors
    assert sections["latest"] and sections["trending"] and sections["top_rated"] and sections["upcoming"]

class MalformedClient(FakeClient):
    def top_rated(self,**kwargs): return {"results":"not-a-list"}

def test_homepage_rejects_malformed_section_without_breaking_others():
    sections,errors=load_homepage_sections(MalformedClient())
    assert sections["top_rated"]==[] and "top_rated" in errors
    assert sections["trending"]

def test_legacy_cached_homepage_fetches_missing_latest_without_reloading_other_shelves():
    client=FakeClient()
    cached={"now_playing":[{"id":99}],"trending":[{"id":1}],"popular":[{"id":2}],"top_rated":[{"id":3}],"upcoming":[{"id":4}]}
    sections,errors=complete_homepage_sections(client,cached,{},"en-US","US")
    assert tuple(sections)==SECTION_KEYS
    assert [movie["id"] for movie in sections["latest"]]==[10,11]
    assert sections["trending"]==cached["trending"]
    assert client.calls==[("now_playing",{"language":"en-US","region":"US"})]
    assert errors=={}

def test_missing_latest_failure_keeps_other_cached_sections_visible():
    class FailingLatest(FakeClient):
        def now_playing(self,**kwargs): raise RuntimeError("TMDB temporarily unavailable")

    cached={"trending":[{"id":1}],"popular":[{"id":2}],"top_rated":[{"id":3}],"upcoming":[{"id":4}]}
    sections,errors=complete_homepage_sections(FailingLatest(),cached,{})
    assert tuple(sections)==SECTION_KEYS
    assert sections["latest"]==[]
    assert "TMDB temporarily unavailable" in errors["latest"]
    assert all(sections[key]==cached[key] for key in cached)

