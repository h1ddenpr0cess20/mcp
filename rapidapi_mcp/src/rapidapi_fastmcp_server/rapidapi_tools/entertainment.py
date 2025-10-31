"""RapidAPI integrations for entertainment-related tools."""

from typing import Any
from urllib.parse import quote

from .client import RapidAPIClient, clean_dict


async def search_imdb(
    search_term: str,
    *,
    search_type: str | None = None,
    first: int = 20,
    country: str = "US",
    language: str = "en-US",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search IMDB for movies, TV shows, people, and more."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "searchTerm": search_term,
            "first": min(first, 50),
            "country": country,
            "language": language,
            "type": search_type,
        }
    )
    data = await client.get("https://imdb8.p.rapidapi.com/v2/search", params=params)
    return {
        "search_term": search_term,
        "results": data.get("data", []),
        "count": len(data.get("data", []) or []),
    }


async def get_title_details(
    title_id: str,
    *,
    country: str = "US",
    language: str = "en-US",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve overview details for a specific IMDB title."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "tconst": title_id,
            "country": country,
            "language": language,
        }
    )
    data = await client.get("https://imdb8.p.rapidapi.com/title/v2/get-overview", params=params)
    return {"title_id": title_id, "data": data.get("data", data)}


async def get_actor_details(
    person_id: str,
    *,
    first: int = 20,
    country: str = "US",
    language: str = "en-US",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve overview details for an IMDB person."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "nconst": person_id,
            "first": min(first, 50),
            "country": country,
            "language": language,
        }
    )
    data = await client.get("https://imdb8.p.rapidapi.com/actors/v2/get-overview", params=params)
    return {"person_id": person_id, "data": data.get("data", data)}


async def steam_search_games(
    term: str,
    *,
    page: int = 1,
    type: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search the Steam store for games."""

    client = client or RapidAPIClient()
    encoded_term = quote(term, safe="")
    url = f"https://steam2.p.rapidapi.com/search/{encoded_term}/page/{page}"
    data = await client.get(url)
    return {
        "term": term,
        "page": page,
        "type": type,
        "results": data,
    }


async def steam_get_app_details(
    app_id: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch details for a specific Steam application."""

    client = client or RapidAPIClient()
    url = f"https://steam2.p.rapidapi.com/appDetail/{app_id}"
    data = await client.get(url)
    return {"app_id": app_id, "data": data}


async def steam_get_app_reviews(
    app_id: str,
    *,
    limit: int = 40,
    cursor: str | None = None,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch reviews for a Steam application."""

    client = client or RapidAPIClient()
    limit = min(limit, 200)
    url = f"https://steam2.p.rapidapi.com/appReviews/{app_id}/limit/{limit}/*"
    params = clean_dict({"cursor": cursor})
    data = await client.get(url, params=params or None)
    return {
        "app_id": app_id,
        "limit": limit,
        "cursor": cursor,
        "reviews": data,
    }


async def search_spotify(
    query: str,
    *,
    search_type: str = "multi",
    offset: int = 0,
    limit: int = 10,
    number_of_top_results: int = 5,
    gl: str = "US",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Search Spotify for tracks, albums, artists, and more."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "q": query,
            "type": search_type,
            "offset": offset,
            "limit": limit,
            "numberOfTopResults": number_of_top_results,
            "gl": gl,
        }
    )
    data = await client.get("https://spotify23.p.rapidapi.com/search/", params=params)
    tracks = data.get("tracks", {}).get("items", []) if isinstance(data.get("tracks"), dict) else []
    return {
        "query": query,
        "type": search_type,
        "results": data,
        "count": len(tracks),
    }


async def get_spotify_albums(
    ids: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve information for one or more Spotify albums."""

    client = client or RapidAPIClient()
    url = "https://spotify23.p.rapidapi.com/albums/"
    data = await client.get(url, params={"ids": ids})
    albums = data.get("albums", []) or []
    return {"ids": ids, "albums": albums, "count": len(albums)}


async def get_spotify_artists(
    ids: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Retrieve information for one or more Spotify artists."""

    client = client or RapidAPIClient()
    url = "https://spotify23.p.rapidapi.com/artists/"
    data = await client.get(url, params={"ids": ids})
    artists = data.get("artists", []) or []
    return {"ids": ids, "artists": artists, "count": len(artists)}


async def get_spotify_artist_overview(
    artist_id: str,
    *,
    gl: str = "US",
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch overview information for a Spotify artist."""

    client = client or RapidAPIClient()
    params = clean_dict({"id": artist_id, "gl": gl})
    data = await client.get("https://spotify23.p.rapidapi.com/artist_overview/", params=params)
    return {"id": artist_id, "overview": data}


async def get_spotify_related_artists(
    artist_id: str,
    *,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch related artists for a Spotify artist."""

    client = client or RapidAPIClient()
    data = await client.get("https://spotify23.p.rapidapi.com/artist_related/", params={"id": artist_id})
    related = data.get("artists", []) or []
    return {"id": artist_id, "related_artists": related, "count": len(related)}


async def get_spotify_artist_albums(
    artist_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
    client: RapidAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch the albums published by a Spotify artist."""

    client = client or RapidAPIClient()
    params = clean_dict(
        {
            "id": artist_id,
            "offset": offset,
            "limit": limit,
        }
    )
    data = await client.get("https://spotify23.p.rapidapi.com/artist_albums/", params=params)
    albums_data = data.get("data", data)
    items = []
    total_count = data.get("totalCount")
    if isinstance(albums_data, dict) and "items" in albums_data:
        items = albums_data.get("items", [])
    elif isinstance(albums_data, list):
        items = albums_data
    return {
        "id": artist_id,
        "albums": albums_data,
        "count": len(items),
        "total_count": total_count if total_count is not None else len(items),
    }
