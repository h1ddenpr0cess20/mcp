"""FastMCP server exposing RapidAPI entertainment tools."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
from servers.base import build_server
from rapidapi_tools import (
    get_actor_details,
    get_spotify_albums,
    get_spotify_artist_albums,
    get_spotify_artist_overview,
    get_spotify_artists,
    get_spotify_related_artists,
    get_title_details,
    search_imdb,
    search_spotify,
    steam_get_app_details,
    steam_get_app_reviews,
    steam_search_games,
)

from .base import build_server

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI entertainment integrations, including IMDB, "
    "Steam, and Spotify endpoints. Set RAPIDAPI_KEY via environment or .env before "
    "launching."
)

server = build_server(
    "rapidapi-entertainment",
    INSTRUCTIONS,
    [
        (search_imdb, "search_imdb", "Search the IMDB catalogue."),
        (get_title_details, "get_title_details", "Retrieve IMDB title details."),
        (get_actor_details, "get_actor_details", "Retrieve IMDB person details."),
        (steam_search_games, "steam_search_games", "Search the Steam store."),
        (steam_get_app_details, "steam_get_app_details", "Fetch Steam app metadata."),
        (steam_get_app_reviews, "steam_get_app_reviews", "Fetch Steam app reviews."),
        (search_spotify, "search_spotify", "Search Spotify content."),
        (get_spotify_albums, "get_spotify_albums", "Fetch Spotify album details."),
        (get_spotify_artists, "get_spotify_artists", "Fetch Spotify artist details."),
        (
            get_spotify_artist_overview,
            "get_spotify_artist_overview",
            "Fetch overview data for a Spotify artist.",
        ),
        (
            get_spotify_related_artists,
            "get_spotify_related_artists",
            "Fetch related artists for a Spotify artist.",
        ),
        (
            get_spotify_artist_albums,
            "get_spotify_artist_albums",
            "Fetch albums released by a Spotify artist.",
        ),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9404


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the entertainment server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
