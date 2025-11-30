import os
from typing import Optional, Any, Dict

from fastmcp import FastMCP

from lastfm_client.client import (
    AlbumAPI,
    ArtistAPI,
    ChartAPI,
    GeoAPI,
    LibraryAPI,
    TagAPI,
    TrackAPI,
    UserAPI,
)

# Initialize MCP server
mcp = FastMCP("lastfm")


def _clients() -> Dict[str, Any]:
    """Create and return initialized Last.fm API client instances.

    Returns:
        Dict mapping API names to their corresponding client instances.
    """
    api_key = os.getenv("LASTFM_API_KEY", "")
    api_secret = os.getenv("LASTFM_API_SECRET", "")
    session_key = os.getenv("LASTFM_SESSION_KEY", "")
    # instantiate clients per type
    return {
        "album": AlbumAPI(api_key, api_secret, session_key),
        "artist": ArtistAPI(api_key, api_secret, session_key),
        "chart": ChartAPI(api_key, api_secret, session_key),
        "geo": GeoAPI(api_key, api_secret, session_key),
        "library": LibraryAPI(api_key, api_secret, session_key),
        "tag": TagAPI(api_key, api_secret, session_key),
        "track": TrackAPI(api_key, api_secret, session_key),
        "user": UserAPI(api_key, api_secret, session_key),
    }


# -------- Album tools --------
@mcp.tool(description="album.getInfo — Get album metadata & tracks")
def album_get_info(
    artist: Optional[str] = None,
    album: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    username: Optional[str] = None,
    lang: Optional[str] = None,
):
    """Get album metadata & tracks.

    Args:
        artist: The artist name.
        album: The album name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled names (0 or 1).
        username: Username whose library album info to fetch.
        lang: Language for descriptions.

    Returns:
        Dict containing album information.
    """
    return _clients()["album"].get_info(
        artist, album, mbid, autocorrect, username, lang
    )


@mcp.tool(description="album.getTags — Get a user's tags for an album")
def album_get_tags(
    artist: Optional[str] = None,
    album: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    user: Optional[str] = None,
):
    """Get a user's tags for an album.

    Args:
        artist: The artist name.
        album: The album name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled names.
        user: The username to get tags for.

    Returns:
        Dict containing album tags.
    """
    return _clients()["album"].get_tags(artist, album, mbid, autocorrect, user)


@mcp.tool(description="album.getTopTags — Get top tags for an album")
def album_get_top_tags(
    artist: Optional[str] = None,
    album: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
):
    """Get top tags for an album.

    Args:
        artist: The artist name.
        album: The album name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled names.

    Returns:
        Dict containing top album tags.
    """
    return _clients()["album"].get_top_tags(artist, album, mbid, autocorrect)


@mcp.tool(description="album.search — Search for albums")
def album_search(
    album: str,
    limit: Optional[int] = None,
    page: Optional[int] = None
):
    """Search for albums.

    Args:
        album: The album name to search for.
        limit: Number of results to return.
        page: Page number for pagination.

    Returns:
        Dict containing search results.
    """
    return _clients()["album"].search(album, limit, page)


# -------- Artist tools --------
@mcp.tool(description="artist.getCorrection — Get canonical correction for artist name")
def artist_get_correction(
    artist: str
):
    """Get canonical correction for artist name.

    Args:
        artist: The artist name to correct.

    Returns:
        Dict containing corrected artist information.
    """
    return _clients()["artist"].get_correction(artist)


@mcp.tool(description="artist.getInfo — Get artist info")
def artist_get_info(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    lang: Optional[str] = None,
    autocorrect: Optional[int] = None,
    username: Optional[str] = None,
):
    """Get artist info.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        lang: Language for descriptions (ISO 639-1 alpha-2).
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).
        username: Username for additional user-specific info.

    Returns:
        Dict containing artist information.
    """
    return _clients()["artist"].get_info(artist, mbid, lang, autocorrect, username)


@mcp.tool(description="artist.getSimilar — Get similar artists")
def artist_get_similar(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Get similar artists.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).
        limit: Maximum number of similar artists to return.

    Returns:
        Dict containing similar artists.
    """
    return _clients()["artist"].get_similar(artist, mbid, autocorrect, limit)


@mcp.tool(description="artist.getTags — Get a user's tags for an artist")
def artist_get_tags(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    user: Optional[str] = None,
    autocorrect: Optional[int] = None,
):
    """Get a user's tags for an artist.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        user: The username to get tags for.
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).

    Returns:
        Dict containing user tags for the artist.
    """
    return _clients()["artist"].get_tags(artist, mbid, user, autocorrect)


@mcp.tool(description="artist.getTopAlbums — Top albums by artist")
def artist_get_top_albums(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Top albums by artist.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top albums.
    """
    return _clients()["artist"].get_top_albums(artist, mbid, autocorrect, page, limit)


@mcp.tool(description="artist.getTopTags — Top tags for artist")
def artist_get_top_tags(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
):
    """Top tags for artist.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).

    Returns:
        Dict containing top tags.
    """
    return _clients()["artist"].get_top_tags(artist, mbid, autocorrect)


@mcp.tool(description="artist.getTopTracks — Top tracks by artist")
def artist_get_top_tracks(
    artist: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Top tracks by artist.

    Args:
        artist: The artist name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist names (0 or 1).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top tracks.
    """
    return _clients()["artist"].get_top_tracks(artist, mbid, autocorrect, page, limit)


@mcp.tool(description="artist.search — Search for artists")
def artist_search(artist: str, limit: Optional[int] = None, page: Optional[int] = None):
    """Search for artists.

    Args:
        artist: The artist name to search for.
        limit: Number of results to return.
        page: Page number for pagination.

    Returns:
        Dict containing search results.
    """
    return _clients()["artist"].search(artist, limit, page)


# -------- Chart tools --------
@mcp.tool(description="chart.getTopArtists — Global top artists")
def chart_get_top_artists(page: Optional[int] = None, limit: Optional[int] = None):
    """Global top artists.

    Args:
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top artists chart data.
    """
    return _clients()["chart"].get_top_artists(page, limit)


@mcp.tool(description="chart.getTopTags — Global top tags")
def chart_get_top_tags(page: Optional[int] = None, limit: Optional[int] = None):
    """Global top tags.

    Args:
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top tags chart data.
    """
    return _clients()["chart"].get_top_tags(page, limit)


@mcp.tool(description="chart.getTopTracks — Global top tracks")
def chart_get_top_tracks(page: Optional[int] = None, limit: Optional[int] = None):
    """Global top tracks.

    Args:
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top tracks chart data.
    """
    return _clients()["chart"].get_top_tracks(page, limit)


# -------- Geo tools --------
@mcp.tool(description="geo.getTopArtists — Top artists by country")
def geo_get_top_artists(
    country: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Top artists by country.

    Args:
        country: Country name.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top artists by country.
    """
    return _clients()["geo"].get_top_artists(country, page, limit)


@mcp.tool(description="geo.getTopTracks — Top tracks by country/metro")
def geo_get_top_tracks(
    country: str,
    location: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Top tracks by country/metro.

    Args:
        country: Country name.
        location: Metro or city name (e.g., "Manchester" for UK).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top tracks by location.
    """
    return _clients()["geo"].get_top_tracks(country, location, page, limit)


# -------- Library tools --------
@mcp.tool(description="library.getArtists — Artists in a user's library")
def library_get_artists(
    user: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Artists in a user's library.

    Args:
        user: Username whose library to retrieve.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing artists from user's library.
    """
    return _clients()["library"].get_artists(user, page, limit)


# -------- Tag tools --------
@mcp.tool(description="tag.getInfo — Tag metadata and wiki")
def tag_get_info(tag: str, lang: Optional[str] = None):
    """Tag metadata and wiki.

    Args:
        tag: The tag name.
        lang: Language for wiki content (ISO 639-1 alpha-2).

    Returns:
        Dict containing tag information.
    """
    return _clients()["tag"].get_info(tag, lang)


@mcp.tool(description="tag.getSimilar — Similar tags")
def tag_get_similar(tag: str):
    """Similar tags.

    Args:
        tag: The tag name to find similar tags for.

    Returns:
        Dict containing similar tags.
    """
    return _clients()["tag"].get_similar(tag)


@mcp.tool(description="tag.getTopAlbums — Top albums for a tag")
def tag_get_top_albums(
    tag: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Top albums for a tag.

    Args:
        tag: The tag name.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top albums for the tag.
    """
    return _clients()["tag"].get_top_albums(tag, page, limit)


@mcp.tool(description="tag.getTopArtists — Top artists for a tag")
def tag_get_top_artists(
    tag: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Top artists for a tag.

    Args:
        tag: The tag name.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top artists for the tag.
    """
    return _clients()["tag"].get_top_artists(tag, page, limit)


@mcp.tool(description="tag.getTopTags — Global top tags")
def tag_get_top_tags():
    """Global top tags.

    Returns:
        Dict containing global top tags.
    """
    return _clients()["tag"].get_top_tags()


@mcp.tool(description="tag.getTopTracks — Top tracks for a tag")
def tag_get_top_tracks(
    tag: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Top tracks for a tag.

    Args:
        tag: The tag name.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing top tracks for the tag.
    """
    return _clients()["tag"].get_top_tracks(tag, page, limit)


@mcp.tool(description="tag.getWeeklyChartList — Weekly chart date ranges for a tag")
def tag_get_weekly_chart_list(tag: str):
    """Weekly chart date ranges for a tag.

    Args:
        tag: The tag name.

    Returns:
        Dict containing available weekly chart date ranges.
    """
    return _clients()["tag"].get_weekly_chart_list(tag)


# -------- Track tools --------
@mcp.tool(description="track.getCorrection — Canonical correction for track")
def track_get_correction(artist: str, track: str):
    """Canonical correction for track.

    Args:
        artist: The artist name.
        track: The track name.

    Returns:
        Dict containing corrected track information.
    """
    return _clients()["track"].get_correction(artist, track)


@mcp.tool(description="track.getInfo — Track info")
def track_get_info(
    artist: Optional[str] = None,
    track: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    username: Optional[str] = None,
):
    """Track info.

    Args:
        artist: The artist name.
        track: The track name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).
        username: Username for additional user-specific info.

    Returns:
        Dict containing track information.
    """
    return _clients()["track"].get_info(artist, track, mbid, autocorrect, username)


@mcp.tool(description="track.getSimilar — Similar tracks")
def track_get_similar(
    artist: Optional[str] = None,
    track: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Similar tracks.

    Args:
        artist: The artist name.
        track: The track name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).
        limit: Maximum number of similar tracks to return.

    Returns:
        Dict containing similar tracks.
    """
    return _clients()["track"].get_similar(artist, track, mbid, autocorrect, limit)


@mcp.tool(description="track.getTags — User's tags for a track")
def track_get_tags(
    artist: Optional[str] = None,
    track: Optional[str] = None,
    mbid: Optional[str] = None,
    user: Optional[str] = None,
    autocorrect: Optional[int] = None,
):
    """User's tags for a track.

    Args:
        artist: The artist name.
        track: The track name.
        mbid: MusicBrainz ID.
        user: The username to get tags for.
        autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).

    Returns:
        Dict containing user tags for the track.
    """
    return _clients()["track"].get_tags(artist, track, mbid, user, autocorrect)


@mcp.tool(description="track.getTopTags — Top tags for a track")
def track_get_top_tags(
    artist: Optional[str] = None,
    track: Optional[str] = None,
    mbid: Optional[str] = None,
    autocorrect: Optional[int] = None,
):
    """Top tags for a track.

    Args:
        artist: The artist name.
        track: The track name.
        mbid: MusicBrainz ID.
        autocorrect: Whether to autocorrect misspelled artist/track names (0 or 1).

    Returns:
        Dict containing top tags for the track.
    """
    return _clients()["track"].get_top_tags(artist, track, mbid, autocorrect)


@mcp.tool(description="track.search — Search for tracks")
def track_search(
    track: str,
    artist: Optional[str] = None,
    limit: Optional[int] = None,
    page: Optional[int] = None,
):
    """Search for tracks.

    Args:
        track: The track name to search for.
        artist: The artist name (optional filter).
        limit: Number of results to return.
        page: Page number for pagination.

    Returns:
        Dict containing search results.
    """
    return _clients()["track"].search(track, artist, limit, page)


# -------- User tools --------
@mcp.tool(description="user.getFriends — Get a user's friends")
def user_get_friends(
    user: str,
    recent_tracks: Optional[bool] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Get a user's friends.

    Args:
        user: Username whose friends to retrieve.
        recent_tracks: Whether to include recent tracks for friends.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing user's friends.
    """
    return _clients()["user"].get_friends(user, recent_tracks, page, limit)


@mcp.tool(description="user.getInfo — Get user profile info")
def user_get_info(user: Optional[str] = None):
    """Get user profile info.

    Args:
        user: Username to get info for.

    Returns:
        Dict containing user profile information.
    """
    return _clients()["user"].get_info(user)


@mcp.tool(description="user.getLovedTracks — Loved tracks by user")
def user_get_loved_tracks(
    user: str, page: Optional[int] = None, limit: Optional[int] = None
):
    """Loved tracks by user.

    Args:
        user: Username whose loved tracks to retrieve.
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing user's loved tracks.
    """
    return _clients()["user"].get_loved_tracks(user, page, limit)


@mcp.tool(
    description="user.getPersonalTags — Personal tags for a type (artist/album/track)"
)
def user_get_personal_tags(user: str, tag: str, tagging_type: str):
    """Personal tags for a type (artist/album/track).

    Args:
        user: Username whose personal tags to retrieve.
        tag: The personal tag name.
        tagging_type: Type to retrieve tags for ('artist', 'album', 'track').

    Returns:
        Dict containing personal tags for the specified type.
    """
    return _clients()["user"].get_personal_tags(user, tag, tagging_type)


@mcp.tool(description="user.getRecentTracks — Recent tracks listened by user")
def user_get_recent_tracks(
    user: str,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    from_timestamp: Optional[int] = None,
    to_timestamp: Optional[int] = None,
):
    """Recent tracks listened by user.

    Args:
        user: Username whose recent tracks to retrieve.
        page: Page number for pagination.
        limit: Number of results per page.
        from_timestamp: Unix timestamp to start from.
        to_timestamp: Unix timestamp to end at.

    Returns:
        Dict containing user's recent tracks.
    """
    return _clients()["user"].get_recent_tracks(
        user, page, limit, from_timestamp, to_timestamp
    )


@mcp.tool(description="user.getTopAlbums — User's top albums")
def user_get_top_albums(
    user: str,
    period: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """User's top albums.

    Args:
        user: Username whose top albums to retrieve.
        period: Time period ('overall', '7day', '1month', etc.).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing user's top albums.
    """
    return _clients()["user"].get_top_albums(user, period, page, limit)


@mcp.tool(description="user.getTopArtists — User's top artists")
def user_get_top_artists(
    user: str,
    period: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """User's top artists.

    Args:
        user: Username whose top artists to retrieve.
        period: Time period ('overall', '7day', '1month', etc.).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing user's top artists.
    """
    return _clients()["user"].get_top_artists(user, period, page, limit)


@mcp.tool(description="user.getTopTags — User's top tags")
def user_get_top_tags(user: str):
    """User's top tags.

    Args:
        user: Username whose top tags to retrieve.

    Returns:
        Dict containing user's top tags.
    """
    return _clients()["user"].get_top_tags(user)


@mcp.tool(description="user.getTopTracks — User's top tracks")
def user_get_top_tracks(
    user: str,
    period: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
):
    """User's top tracks.

    Args:
        user: Username whose top tracks to retrieve.
        period: Time period ('overall', '7day', '1month', etc.).
        page: Page number for pagination.
        limit: Number of results per page.

    Returns:
        Dict containing user's top tracks.
    """
    return _clients()["user"].get_top_tracks(user, period, page, limit)


@mcp.tool(description="user.getWeeklyAlbumChart — Weekly album chart for user")
def user_get_weekly_album_chart(
    user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None
):
    """Weekly album chart for user.

    Args:
        user: Username whose weekly album chart to retrieve.
        from_timestamp: Unix timestamp for start of week.
        to_timestamp: Unix timestamp for end of week.

    Returns:
        Dict containing weekly album chart data.
    """
    return _clients()["user"].get_weekly_album_chart(user, from_timestamp, to_timestamp)


@mcp.tool(description="user.getWeeklyArtistChart — Weekly artist chart for user")
def user_get_weekly_artist_chart(
    user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None
):
    """Weekly artist chart for user.

    Args:
        user: Username whose weekly artist chart to retrieve.
        from_timestamp: Unix timestamp for start of week.
        to_timestamp: Unix timestamp for end of week.

    Returns:
        Dict containing weekly artist chart data.
    """
    return _clients()["user"].get_weekly_artist_chart(
        user, from_timestamp, to_timestamp
    )


@mcp.tool(
    description="user.getWeeklyChartList — Available weekly chart ranges for user"
)
def user_get_weekly_chart_list(user: str):
    """Available weekly chart ranges for user.

    Args:
        user: Username whose weekly chart list to retrieve.

    Returns:
        Dict containing available weekly chart date ranges.
    """
    return _clients()["user"].get_weekly_chart_list(user)


@mcp.tool(description="user.getWeeklyTrackChart — Weekly track chart for user")
def user_get_weekly_track_chart(
    user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None
):
    """Weekly track chart for user.

    Args:
        user: Username whose weekly track chart to retrieve.
        from_timestamp: Unix timestamp for start of week.
        to_timestamp: Unix timestamp for end of week.

    Returns:
        Dict containing weekly track chart data.
    """
    return _clients()["user"].get_weekly_track_chart(user, from_timestamp, to_timestamp)


if __name__ == "__main__":
    # Start the MCP server process (FastMCP will handle transport when launched by a client)
    mcp.run()
    # mcp.run(transport="http", host="127.0.0.1", port=8000)
