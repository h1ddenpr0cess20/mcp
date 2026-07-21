"""FastMCP server exposing RapidAPI social media tools."""

from __future__ import annotations

from .base import build_server
from ..rapidapi_tools import (
    get_trending_topics,
    get_tweet_details,
    get_user_profile,
    get_user_tweets,
    search_tweets,
    search_users,
)


INSTRUCTIONS = (
    "This server wraps the Tyumi RapidAPI social integrations powered by Twitter154 "
    "and related endpoints. Make sure RAPIDAPI_KEY is available via environment or "
    ".env before starting."
)

server = build_server(
    "rapidapi-social",
    INSTRUCTIONS,
    [
        (search_tweets, "search_tweets", "Search tweets via Twitter154."),
        (get_user_profile, "get_user_profile", "Fetch a Twitter profile."),
        (get_user_tweets, "get_user_tweets", "Fetch recent tweets from a user."),
        (get_trending_topics, "get_trending_topics", "Fetch trending topics."),
        (get_tweet_details, "get_tweet_details", "Fetch a single tweet's details."),
        (search_users, "search_users", "Search for Twitter users."),
    ],
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9405


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, force_http: bool = False) -> None:
    """Run the social server. HTTP if launched directly or force_http, stdio if piped."""
    import sys
    if force_http or sys.stdin.isatty():
        from rapidapi_client.http_compat import serve_http

        serve_http(server, host=host, port=port, path="/mcp")
    else:
        server.run()


if __name__ == "__main__":
    run_server()
