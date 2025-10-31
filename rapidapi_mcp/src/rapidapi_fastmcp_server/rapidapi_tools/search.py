"""RapidAPI integrations for search and news tools."""

from typing import Any

from .client import RapidAPIClient, bool_to_str, clean_dict


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


async def local_business_search(
    query: str,
    *,
    limit: int = 20,
    lat: float | None = None,
    lng: float | None = None,
    zoom: int = 13,
    language: str = "en",
    region: str = "us",
    extract_emails_and_contacts: bool = False,
    subtypes: str | None = None,
    verified: bool = False,
    business_status: str | None = None,
    fields: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search for local businesses."""

    client = client or RapidAPIClient()
    limit = min(limit, 50)
    params = clean_dict(
        {
            "query": query,
            "limit": limit,
            "lat": lat,
            "lng": lng,
            "zoom": zoom,
            "language": language,
            "region": region,
            "extract_emails_and_contacts": bool_to_str(extract_emails_and_contacts),
            "subtypes": subtypes,
            "verified": bool_to_str(verified),
            "business_status": business_status,
            "fields": fields,
        }
    )
    data = await client.get("https://local-business-data.p.rapidapi.com/search", params=params)
    businesses = data.get("data", []) or []
    return {
        "query": query,
        "businesses": businesses,
        "count": len(businesses),
    }


async def get_business_details(
    business_id: str,
    *,
    extract_emails_and_contacts: bool | None = None,
    extract_share_link: bool | None = None,
    fields: str | None = None,
    region: str | None = None,
    language: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve detailed information for a business."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "business_id": business_id,
            "extract_emails_and_contacts": bool_to_str(extract_emails_and_contacts) if extract_emails_and_contacts is not None else None,
            "extract_share_link": bool_to_str(extract_share_link) if extract_share_link is not None else None,
            "fields": fields,
            "region": region,
            "language": language,
        }
    )
    data = await client.get("https://local-business-data.p.rapidapi.com/business-details", params=params)
    return {"business_id": business_id, "business": data.get("data", {})}


async def get_business_reviews(
    business_id: str,
    *,
    limit: int | None = None,
    offset: int | None = None,
    translate_reviews: bool | None = None,
    query: str | None = None,
    sort_by: str | None = None,
    fields: str | None = None,
    region: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve reviews for a business."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "business_id": business_id,
            "limit": limit,
            "offset": offset,
            "translate_reviews": bool_to_str(translate_reviews) if translate_reviews is not None else None,
            "query": query,
            "sort_by": sort_by,
            "fields": fields,
            "region": region,
        }
    )
    data = await client.get("https://local-business-data.p.rapidapi.com/business-reviews", params=params)
    reviews = data.get("data", []) or []
    return {"business_id": business_id, "reviews": reviews, "count": len(reviews)}
