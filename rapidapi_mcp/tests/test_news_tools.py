import asyncio

from rapidapi_client.rapidapi_tools.news import (
    get_full_story_coverage,
    get_headlines,
    get_local_headlines,
    search_news,
)


class StubRapidAPIClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def get(self, url, *, params=None, headers=None):
        self.calls.append({"url": url, "params": params})
        return self.payload


def test_search_news_strips_sub_articles():
    payload = {
        "data": [
            {"title": "Example", "sub_articles": [{"title": "detail"}], "source": "test"}
        ]
    }
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        search_news(
            "quantum computing",
            limit=5,
            time_published="24h",
            country="UK",
            lang="en",
            source="guardian",
            client=client,
        )
    )

    call = client.calls[0]
    assert call["url"] == "https://real-time-news-data.p.rapidapi.com/search"
    assert call["params"]["query"] == "quantum computing"
    assert call["params"]["limit"] == 5
    assert call["params"]["source"] == "guardian"

    assert result["count"] == 1
    article = result["articles"][0]
    assert article["title"] == "Example"
    assert "sub_articles" not in article


def test_get_headlines_uses_defaults_and_strips_sub_articles():
    payload = {
        "data": [{"title": "Top Story", "sub_articles": [{"title": "child"}]}]
    }
    client = StubRapidAPIClient(payload)

    result = asyncio.run(get_headlines(limit=3, country="CA", lang="fr", client=client))

    call = client.calls[0]
    assert call["params"] == {"limit": 3, "country": "CA", "lang": "fr"}

    assert result["count"] == 1
    assert result["headlines"][0]["title"] == "Top Story"
    assert "sub_articles" not in result["headlines"][0]


def test_get_local_headlines_passes_query():
    payload = {"data": [{"title": "Local Update", "sub_articles": []}]}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        get_local_headlines(
            "toronto",
            limit=2,
            country="CA",
            lang="en",
            client=client,
        )
    )

    call = client.calls[0]
    assert call["params"]["query"] == "toronto"
    assert call["params"]["limit"] == 2
    assert result["query"] == "toronto"
    assert result["count"] == 1


def test_get_full_story_coverage_returns_articles():
    payload = {"data": [{"title": "Story", "sub_articles": [{"title": "child"}]}]}
    client = StubRapidAPIClient(payload)

    result = asyncio.run(
        get_full_story_coverage("story-id", sort="NEWEST", client=client)
    )

    call = client.calls[0]
    assert call["params"] == {"story_id": "story-id", "sort": "NEWEST"}
    assert result["story_id"] == "story-id"
    assert result["count"] == 1
    assert result["articles"][0]["title"] == "Story"
    assert "sub_articles" not in result["articles"][0]
