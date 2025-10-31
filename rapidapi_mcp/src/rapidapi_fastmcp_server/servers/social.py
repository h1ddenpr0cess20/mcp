"""FastMCP server exposing RapidAPI social media tools."""

if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
from servers.base import build_server
from rapidapi_tools import (
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


def run_server(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run the social server using the HTTP transport."""

    server.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    run_server()
