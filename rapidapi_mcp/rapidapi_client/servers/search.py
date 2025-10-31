"""FastMCP server exposing RapidAPI web and local business search tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import (
    get_business_details,
    get_business_reviews,
    local_business_search,
    search_web,
)

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI web and local business search integrations. "
    "Ensure RAPIDAPI_KEY is configured via environment or .env prior to launch."
)

server = build_server(
    "rapidapi-search",
    INSTRUCTIONS,
    [
        (   search_web, 
            "search_web",
            "Supports all Google Advanced Search operators (site:, inurl:, intitle:, etc)."),
        (
            local_business_search,
            "local_business_search",
            "Search for local businesses using Local Business Data.",
        ),
        (
            get_business_details,
            "get_business_details",
            "Retrieve Local Business Data details for a business.",
        ),
        (
            get_business_reviews,
            "get_business_reviews",
            "Retrieve Local Business Data reviews for a business.",
        ),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9408


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the search server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
