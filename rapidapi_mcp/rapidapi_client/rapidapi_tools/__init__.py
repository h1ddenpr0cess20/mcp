"""Collection of Python wrappers for RapidAPI-powered tools."""

from .client import MissingRapidAPIKeyError, RapidAPIClient
from .entertainment import (
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
from .finance import get_twelve_data_price, get_twelve_data_quote
from .food import search_recipes
from .jobs import get_job_details, search_jobs
from .realestate import get_property_details, search_rental_properties
from .news import (
    get_full_story_coverage,
    get_headlines,
    get_local_headlines,
    search_news,
)
from .search import (
    get_business_details,
    get_business_reviews,
    local_business_search,
    search_web,
)
from .social import (
    get_trending_topics,
    get_tweet_details,
    get_user_profile,
    get_user_tweets,
    search_tweets,
    search_users,
)

__all__ = [
    "MissingRapidAPIKeyError",
    "RapidAPIClient",
    "search_jobs",
    "get_job_details",
    "get_twelve_data_price",
    "get_twelve_data_quote",
    "search_recipes",
    "search_imdb",
    "get_title_details",
    "get_actor_details",
    "steam_search_games",
    "steam_get_app_details",
    "steam_get_app_reviews",
    "search_spotify",
    "get_spotify_albums",
    "get_spotify_artists",
    "get_spotify_artist_overview",
    "get_spotify_related_artists",
    "get_spotify_artist_albums",
    "search_tweets",
    "get_user_profile",
    "get_user_tweets",
    "get_trending_topics",
    "get_tweet_details",
    "search_users",
    "search_rental_properties",
    "get_property_details",
    "search_news",
    "get_headlines",
    "get_local_headlines",
    "get_full_story_coverage",
    "local_business_search",
    "get_business_details",
    "get_business_reviews",
    "search_web",
]
