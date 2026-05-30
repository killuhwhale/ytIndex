from apps.videos.services.search import SearchResult, _snippet_for_query
from apps.videos.services.youtube_url_parser import youtube_timestamp_url


def test_search_result_shape_for_timestamp_url():
    url = youtube_timestamp_url("vid123", 65000)
    result = SearchResult("1", "vid123", "Title", "Channel", None, 65000, 70000, url, "snippet", 0.9, "hybrid", "why")
    assert result.youtube_timestamp_url.endswith("&t=65s")
    assert result.match_type == "hybrid"


def test_search_snippet_centers_query_match():
    text = "intro " * 120 + "needle phrase with important context " + "tail " * 120
    snippet = _snippet_for_query(text, "needle", max_chars=120)

    assert "needle phrase" in snippet
    assert len(snippet) <= 126
