
import os
from typing import Optional, Any, Dict

from fastmcp import FastMCP

from lastfm_client.client import (
    AlbumAPI, ArtistAPI, AuthAPI, ChartAPI, GeoAPI, LibraryAPI,
    TagAPI, TrackAPI, UserAPI
)

# Initialize MCP server
mcp = FastMCP("lastfm")

def _clients() -> Dict[str, Any]:
    api_key = os.getenv("LASTFM_API_KEY", "")
    api_secret = os.getenv("LASTFM_API_SECRET", "")
    session_key = os.getenv("LASTFM_SESSION_KEY", "")
    # instantiate clients per type
    return {
        "album": AlbumAPI(api_key, api_secret, session_key),
        "artist": ArtistAPI(api_key, api_secret, session_key),
        "auth": AuthAPI(api_key, api_secret, session_key),
        "chart": ChartAPI(api_key, api_secret, session_key),
        "geo": GeoAPI(api_key, api_secret, session_key),
        "library": LibraryAPI(api_key, api_secret, session_key),
        "tag": TagAPI(api_key, api_secret, session_key),
        "track": TrackAPI(api_key, api_secret, session_key),
        "user": UserAPI(api_key, api_secret, session_key),
    }

# -------- Album tools --------
@mcp.tool(description="album.addTags — Tag an album (requires auth)")
def album_add_tags(artist: str, album: str, tags: str, sk: Optional[str] = None):
    return _clients()["album"].add_tags(artist, album, tags, sk)

@mcp.tool(description="album.getInfo — Get album metadata & tracks")
def album_get_info(artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                   autocorrect: Optional[int] = None, username: Optional[str] = None, lang: Optional[str] = None):
    return _clients()["album"].get_info(artist, album, mbid, autocorrect, username, lang)

@mcp.tool(description="album.getTags — Get a user's tags for an album")
def album_get_tags(artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                   autocorrect: Optional[int] = None, user: Optional[str] = None):
    return _clients()["album"].get_tags(artist, album, mbid, autocorrect, user)

@mcp.tool(description="album.getTopTags — Get top tags for an album")
def album_get_top_tags(artist: Optional[str] = None, album: Optional[str] = None, mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None):
    return _clients()["album"].get_top_tags(artist, album, mbid, autocorrect)

@mcp.tool(description="album.removeTag — Remove a tag from an album (requires auth)")
def album_remove_tag(artist: str, album: str, tag: str, sk: Optional[str] = None):
    return _clients()["album"].remove_tag(artist, album, tag, sk)

@mcp.tool(description="album.search — Search for albums")
def album_search(album: str, limit: Optional[int] = None, page: Optional[int] = None):
    return _clients()["album"].search(album, limit, page)

# -------- Artist tools --------
@mcp.tool(description="artist.addTags — Tag an artist (requires auth)")
def artist_add_tags(artist: str, tags: str, sk: Optional[str] = None):
    return _clients()["artist"].add_tags(artist, tags, sk)

@mcp.tool(description="artist.getCorrection — Get canonical correction for artist name")
def artist_get_correction(artist: str):
    return _clients()["artist"].get_correction(artist)

@mcp.tool(description="artist.getInfo — Get artist info")
def artist_get_info(artist: Optional[str] = None, mbid: Optional[str] = None, 
                    lang: Optional[str] = None, autocorrect: Optional[int] = None, username: Optional[str] = None):
    return _clients()["artist"].get_info(artist, mbid, lang, autocorrect, username)

@mcp.tool(description="artist.getSimilar — Get similar artists")
def artist_get_similar(artist: Optional[str] = None, mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["artist"].get_similar(artist, mbid, autocorrect, limit)

@mcp.tool(description="artist.getTags — Get a user's tags for an artist")
def artist_get_tags(artist: Optional[str] = None, mbid: Optional[str] = None, user: Optional[str] = None, autocorrect: Optional[int] = None):
    return _clients()["artist"].get_tags(artist, mbid, user, autocorrect)

@mcp.tool(description="artist.getTopAlbums — Top albums by artist")
def artist_get_top_albums(artist: Optional[str] = None, mbid: Optional[str] = None, autocorrect: Optional[int] = None,
                          page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["artist"].get_top_albums(artist, mbid, autocorrect, page, limit)

@mcp.tool(description="artist.getTopTags — Top tags for artist")
def artist_get_top_tags(artist: Optional[str] = None, mbid: Optional[str] = None, autocorrect: Optional[int] = None):
    return _clients()["artist"].get_top_tags(artist, mbid, autocorrect)

@mcp.tool(description="artist.getTopTracks — Top tracks by artist")
def artist_get_top_tracks(artist: Optional[str] = None, mbid: Optional[str] = None, autocorrect: Optional[int] = None,
                          page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["artist"].get_top_tracks(artist, mbid, autocorrect, page, limit)

@mcp.tool(description="artist.removeTag — Remove tag from artist (requires auth)")
def artist_remove_tag(artist: str, tag: str, sk: Optional[str] = None):
    return _clients()["artist"].remove_tag(artist, tag, sk)

@mcp.tool(description="artist.search — Search for artists")
def artist_search(artist: str, limit: Optional[int] = None, page: Optional[int] = None):
    return _clients()["artist"].search(artist, limit, page)

# -------- Auth tools --------
@mcp.tool(description="auth.getMobileSession — Exchange username/password for session (mobile)")
def auth_get_mobile_session(username: str, password: str):
    return _clients()["auth"].get_mobile_session(username, password)

@mcp.tool(description="auth.getSession — Exchange token for session")
def auth_get_session(token: str):
    return _clients()["auth"].get_session(token)

@mcp.tool(description="auth.getToken — Get an unauthorized token")
def auth_get_token():
    return _clients()["auth"].get_token()

# -------- Chart tools --------
@mcp.tool(description="chart.getTopArtists — Global top artists")
def chart_get_top_artists(page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["chart"].get_top_artists(page, limit)

@mcp.tool(description="chart.getTopTags — Global top tags")
def chart_get_top_tags(page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["chart"].get_top_tags(page, limit)

@mcp.tool(description="chart.getTopTracks — Global top tracks")
def chart_get_top_tracks(page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["chart"].get_top_tracks(page, limit)

# -------- Geo tools --------
@mcp.tool(description="geo.getTopArtists — Top artists by country")
def geo_get_top_artists(country: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["geo"].get_top_artists(country, page, limit)

@mcp.tool(description="geo.getTopTracks — Top tracks by country/metro")
def geo_get_top_tracks(country: str, location: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["geo"].get_top_tracks(country, location, page, limit)

# -------- Library tools --------
@mcp.tool(description="library.getArtists — Artists in a user's library")
def library_get_artists(user: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["library"].get_artists(user, page, limit)

# -------- Tag tools --------
@mcp.tool(description="tag.getInfo — Tag metadata and wiki")
def tag_get_info(tag: str, lang: Optional[str] = None):
    return _clients()["tag"].get_info(tag, lang)

@mcp.tool(description="tag.getSimilar — Similar tags")
def tag_get_similar(tag: str):
    return _clients()["tag"].get_similar(tag)

@mcp.tool(description="tag.getTopAlbums — Top albums for a tag")
def tag_get_top_albums(tag: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["tag"].get_top_albums(tag, page, limit)

@mcp.tool(description="tag.getTopArtists — Top artists for a tag")
def tag_get_top_artists(tag: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["tag"].get_top_artists(tag, page, limit)

@mcp.tool(description="tag.getTopTags — Global top tags")
def tag_get_top_tags():
    return _clients()["tag"].get_top_tags()

@mcp.tool(description="tag.getTopTracks — Top tracks for a tag")
def tag_get_top_tracks(tag: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["tag"].get_top_tracks(tag, page, limit)

@mcp.tool(description="tag.getWeeklyChartList — Weekly chart date ranges for a tag")
def tag_get_weekly_chart_list(tag: str):
    return _clients()["tag"].get_weekly_chart_list(tag)

# -------- Track tools --------
@mcp.tool(description="track.addTags — Tag a track (requires auth)")
def track_add_tags(artist: str, track: str, tags: str, sk: Optional[str] = None):
    return _clients()["track"].add_tags(artist, track, tags, sk)

@mcp.tool(description="track.getCorrection — Canonical correction for track")
def track_get_correction(artist: str, track: str):
    return _clients()["track"].get_correction(artist, track)

@mcp.tool(description="track.getInfo — Track info")
def track_get_info(artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                   autocorrect: Optional[int] = None, username: Optional[str] = None):
    return _clients()["track"].get_info(artist, track, mbid, autocorrect, username)

@mcp.tool(description="track.getSimilar — Similar tracks")
def track_get_similar(artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                      autocorrect: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["track"].get_similar(artist, track, mbid, autocorrect, limit)

@mcp.tool(description="track.getTags — User's tags for a track")
def track_get_tags(artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                   user: Optional[str] = None, autocorrect: Optional[int] = None):
    return _clients()["track"].get_tags(artist, track, mbid, user, autocorrect)

@mcp.tool(description="track.getTopTags — Top tags for a track")
def track_get_top_tags(artist: Optional[str] = None, track: Optional[str] = None, mbid: Optional[str] = None,
                       autocorrect: Optional[int] = None):
    return _clients()["track"].get_top_tags(artist, track, mbid, autocorrect)

@mcp.tool(description="track.love — Mark a track as loved (requires auth)")
def track_love(artist: str, track: str, sk: Optional[str] = None):
    return _clients()["track"].love(artist, track, sk)

@mcp.tool(description="track.removeTag — Remove a tag from a track (requires auth)")
def track_remove_tag(artist: str, track: str, tag: str, sk: Optional[str] = None):
    return _clients()["track"].remove_tag(artist, track, tag, sk)

@mcp.tool(description="track.scrobble — Add a scrobble (requires auth)")
def track_scrobble(artist: str, track: str, timestamp: int, album: Optional[str] = None,
                   album_artist: Optional[str] = None, track_number: Optional[int] = None,
                   mbid: Optional[str] = None, duration: Optional[int] = None, sk: Optional[str] = None):
    return _clients()["track"].scrobble(artist, track, timestamp, album, album_artist, track_number, mbid, duration, sk)

@mcp.tool(description="track.search — Search for tracks")
def track_search(track: str, artist: Optional[str] = None, limit: Optional[int] = None, page: Optional[int] = None):
    return _clients()["track"].search(track, artist, limit, page)

@mcp.tool(description="track.unlove — Unmark loved (requires auth)")
def track_unlove(artist: str, track: str, sk: Optional[str] = None):
    return _clients()["track"].unlove(artist, track, sk)

@mcp.tool(description="track.updateNowPlaying — Set now playing (requires auth)")
def track_update_now_playing(artist: str, track: str, album: Optional[str] = None,
                             album_artist: Optional[str] = None, track_number: Optional[int] = None,
                             duration: Optional[int] = None, mbid: Optional[str] = None, sk: Optional[str] = None):
    return _clients()["track"].update_now_playing(artist, track, album, album_artist, track_number, duration, mbid, sk)

# -------- User tools --------
@mcp.tool(description="user.getFriends — Get a user's friends")
def user_get_friends(user: str, recent_tracks: Optional[bool] = None, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["user"].get_friends(user, recent_tracks, page, limit)

@mcp.tool(description="user.getInfo — Get user profile info")
def user_get_info(user: Optional[str] = None):
    return _clients()["user"].get_info(user)

@mcp.tool(description="user.getLovedTracks — Loved tracks by user")
def user_get_loved_tracks(user: str, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["user"].get_loved_tracks(user, page, limit)

@mcp.tool(description="user.getPersonalTags — Personal tags for a type (artist/album/track)")
def user_get_personal_tags(user: str, tag: str, tagging_type: str):
    return _clients()["user"].get_personal_tags(user, tag, tagging_type)

@mcp.tool(description="user.getRecentTracks — Recent tracks listened by user")
def user_get_recent_tracks(user: str, page: Optional[int] = None, limit: Optional[int] = None,
                           from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
    return _clients()["user"].get_recent_tracks(user, page, limit, from_timestamp, to_timestamp)

@mcp.tool(description="user.getTopAlbums — User's top albums")
def user_get_top_albums(user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["user"].get_top_albums(user, period, page, limit)

@mcp.tool(description="user.getTopArtists — User's top artists")
def user_get_top_artists(user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["user"].get_top_artists(user, period, page, limit)

@mcp.tool(description="user.getTopTags — User's top tags")
def user_get_top_tags(user: str):
    return _clients()["user"].get_top_tags(user)

@mcp.tool(description="user.getTopTracks — User's top tracks")
def user_get_top_tracks(user: str, period: Optional[str] = None, page: Optional[int] = None, limit: Optional[int] = None):
    return _clients()["user"].get_top_tracks(user, period, page, limit)

@mcp.tool(description="user.getWeeklyAlbumChart — Weekly album chart for user")
def user_get_weekly_album_chart(user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
    return _clients()["user"].get_weekly_album_chart(user, from_timestamp, to_timestamp)

@mcp.tool(description="user.getWeeklyArtistChart — Weekly artist chart for user")
def user_get_weekly_artist_chart(user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
    return _clients()["user"].get_weekly_artist_chart(user, from_timestamp, to_timestamp)

@mcp.tool(description="user.getWeeklyChartList — Available weekly chart ranges for user")
def user_get_weekly_chart_list(user: str):
    return _clients()["user"].get_weekly_chart_list(user)

@mcp.tool(description="user.getWeeklyTrackChart — Weekly track chart for user")
def user_get_weekly_track_chart(user: str, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None):
    return _clients()["user"].get_weekly_track_chart(user, from_timestamp, to_timestamp)

if __name__ == "__main__":
    # Start the MCP server process (FastMCP will handle transport when launched by a client)
    mcp.run()
    # mcp.run(transport="http", host="127.0.0.1", port=8000)
