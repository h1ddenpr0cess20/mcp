"""FastMCP server exposing RapidAPI real estate tools."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
from servers.base import build_server
from rapidapi_tools import get_property_details, search_rental_properties

INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI real estate integrations powered by Zillow. "
    "Set RAPIDAPI_KEY in the environment or .env before running."
)

server = build_server(
    "rapidapi-realestate",
    INSTRUCTIONS,
    [
        (
            search_rental_properties,
            "search_rental_properties",
            "Search for rental properties using Zillow.",
        ),
        (
            get_property_details,
            "get_property_details",
            "Retrieve detailed information for a Zillow property.",
        ),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9406


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the real estate server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
