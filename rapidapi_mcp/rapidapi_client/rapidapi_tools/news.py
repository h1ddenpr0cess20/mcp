"""RapidAPI integrations for news-focused endpoints."""

from typing import Any

from .client import RapidAPIClient, clean_dict


async def search_news(
    query: str,
    *,
    limit: int = 10,
    time_published: str = "anytime",
    country: str = "US",
    lang: str = "en",
    source: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search the Real-Time News Data API."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "query": query,
            "limit": limit,
            "time_published": time_published,
            "country": country,
            "lang": lang,
            "source": source,
        }
    )
    data = await client.get("https://real-time-news-data.p.rapidapi.com/search", params=params)
    articles = [
        {key: value for key, value in article.items() if key != "sub_articles"}
        for article in data.get("data", []) or []
    ]
    return {
        "query": query,
        "articles": articles,
        "count": len(articles),
    }


async def get_headlines(
    *,
    limit: int = 10,
    country: str = "US",
    lang: str = "en",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve top headlines."""

    client = client or RapidAPIClient()
    params = clean_dict({"limit": limit, "country": country, "lang": lang})
    data = await client.get("https://real-time-news-data.p.rapidapi.com/top-headlines", params=params)
    headlines = [
        {key: value for key, value in headline.items() if key != "sub_articles"}
        for headline in data.get("data", []) or []
    ]
    return {"headlines": headlines, "count": len(headlines)}


async def get_local_headlines(
    query: str,
    *,
    limit: int = 10,
    country: str = "US",
    lang: str = "en",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve local headlines for a query."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "query": query,
            "limit": limit,
            "country": country,
            "lang": lang,
        }
    )
    data = await client.get("https://real-time-news-data.p.rapidapi.com/local-headlines", params=params)
    headlines = [
        {key: value for key, value in headline.items() if key != "sub_articles"}
        for headline in data.get("data", []) or []
    ]
    return {"query": query, "local_headlines": headlines, "count": len(headlines)}


async def get_full_story_coverage(
    story_id: str,
    *,
    sort: str = "RELEVANCE",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve coverage for a specific story."""

    client = client or RapidAPIClient()
    params = clean_dict({"story_id": story_id, "sort": sort})
    data = await client.get(
        "https://real-time-news-data.p.rapidapi.com/full-story-coverage",
        params=params,
    )
    articles = [
        {key: value for key, value in article.items() if key != "sub_articles"}
        for article in data.get("data", []) or []
    ]
    return {"story_id": story_id, "articles": articles, "count": len(articles)}
