"""RapidAPI integrations for social media tools."""

from typing import Any

from .client import RapidAPIClient, bool_to_str, clean_dict


async def search_tweets(
    query: str,
    *,
    limit: int = 20,
    section: str = "top",
    min_retweets: int = 0,
    min_likes: int = 0,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search tweets via the Twitter154 RapidAPI endpoint."""

    client = client or RapidAPIClient()
    limit = min(limit, 100)
    params = clean_dict(
        {
            "query": query,
            "section": section,
            "min_retweets": min_retweets,
            "min_likes": min_likes,
            "limit": limit,
        }
    )
    data = await client.get("https://twitter154.p.rapidapi.com/search/search", params=params)
    results = data.get("results", []) or []
    return {"query": query, "tweets": results, "count": len(results)}


async def get_user_profile(
    username: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve a Twitter user's profile details."""

    client = client or RapidAPIClient()
    data = await client.get("https://twitter154.p.rapidapi.com/user/details", params={"username": username})
    return {"username": username, "profile": data}


async def get_user_tweets(
    username: str,
    *,
    limit: int = 20,
    user_id: str | None = None,
    include_replies: bool = False,
    include_pinned: bool = False,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve recent tweets for a specific user."""

    client = client or RapidAPIClient()
    limit = min(limit, 100)
    params = clean_dict(
        {
            "username": username,
            "limit": limit,
            "include_replies": bool_to_str(include_replies),
            "include_pinned": bool_to_str(include_pinned),
            "user_id": user_id,
        }
    )
    data = await client.get("https://twitter154.p.rapidapi.com/user/tweets", params=params)
    tweets = data.get("results", []) or []
    return {
        "username": username,
        "tweets": tweets,
        "count": len(tweets),
        "params": {
            "limit": limit,
            "user_id": user_id,
            "include_replies": include_replies,
            "include_pinned": include_pinned,
        },
    }


async def get_trending_topics(
    woeid: int = 1,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch trending topics for a WOEID."""

    client = client or RapidAPIClient()
    data = await client.get("https://twitter154.p.rapidapi.com/trends/", params={"woeid": woeid})
    trends = data or []
    return {"woeid": woeid, "trends": trends, "count": len(trends) if isinstance(trends, list) else None}


async def get_tweet_details(
    tweet_id: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve metadata for a specific tweet."""

    client = client or RapidAPIClient()
    data = await client.get("https://twitter154.p.rapidapi.com/tweet/details", params={"tweet_id": tweet_id})
    return {"tweet_id": tweet_id, "tweet": data}


async def search_users(
    query: str,
    *,
    limit: int = 20,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search for Twitter accounts by query."""

    client = client or RapidAPIClient()
    limit = min(limit, 50)
    params = clean_dict({"query": query, "limit": limit})
    data = await client.get("https://twitter154.p.rapidapi.com/search/users", params=params)
    users = data.get("results", []) or []
    return {"query": query, "users": users, "count": len(users)}
