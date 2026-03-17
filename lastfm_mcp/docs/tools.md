# Tool Reference

Complete reference for all tools exposed by the Last.fm MCP server. Tools are grouped by category matching the server's module structure.

Last.fm tags are community-applied labels — words and phrases listeners use to describe artists, albums, and tracks. They work like genre tags but are far more granular: you will find tags like `dark ambient`, `90s hip hop`, `running`, and `female vocalists` alongside conventional genre names. Tags are one of the most powerful tools for music discovery on Last.fm.

> **New to Last.fm?** Last.fm is a music tracking service that scrobbles (records) what you listen to and builds a history of your listening habits. It also maintains a large social music database with artist biographies, similar artist graphs, and community-generated tags.

---

## Table of Contents

- [Album](#album)
- [Artist](#artist)
- [Chart](#chart)
- [Geo](#geo)
- [Library](#library)
- [Tag](#tag)
- [Track](#track)
- [User](#user)

---

## Album

---

### album_get_info

Returns metadata and track listing for an album. Includes play count, listener count, release date, wiki summary, and the full track list with durations.

**Parameters**

| Parameter   | Type    | Required | Description                                                        |
|-------------|---------|----------|--------------------------------------------------------------------|
| artist      | string  | no*      | Artist name. Required unless `mbid` is provided.                   |
| album       | string  | no*      | Album name. Required unless `mbid` is provided.                    |
| mbid        | string  | no       | MusicBrainz ID. Can be used instead of artist + album.             |
| autocorrect | integer | no       | Pass `1` to silently correct misspelled artist and album names.    |
| username    | string  | no       | Include this user's play count for the album in the response.      |
| lang        | string  | no       | Language for the wiki summary. ISO 639-1 code, e.g. `en`, `de`.   |

*You must provide either `artist` + `album`, or `mbid`.

**Returns**

A dictionary with fields including:

| Field        | Description                                       |
|--------------|---------------------------------------------------|
| name         | Album title                                       |
| artist       | Artist name                                       |
| playcount    | Total plays across all Last.fm users              |
| listeners    | Total unique listeners                            |
| tracks       | List of tracks with name, duration, and position  |
| wiki         | Summary and full article text (if available)      |
| tags         | Top community tags for this album                 |
| url          | Last.fm page URL                                  |

**Use cases**

- Get a full track listing and durations for an album.
- Retrieve the wiki summary for an album you are unfamiliar with.
- Check how many listeners an album has as a rough gauge of its popularity.

---

### album_get_tags

Returns the tags a specific user has applied to an album. Tags are personal labels, not the community consensus — they reflect how that one user categorizes the album in their own library.

**Parameters**

| Parameter   | Type    | Required | Description                                               |
|-------------|---------|----------|-----------------------------------------------------------|
| artist      | string  | no*      | Artist name.                                              |
| album       | string  | no*      | Album name.                                               |
| mbid        | string  | no       | MusicBrainz ID.                                           |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.                     |
| user        | string  | no       | The username whose tags to retrieve.                      |

**Returns**

A dictionary containing a list of tag objects, each with `name` and `url` fields.

**Use cases**

- See how a particular user has personally categorized an album.

---

### album_get_top_tags

Returns the top community tags for an album, ranked by how many users have applied them.

**Parameters**

| Parameter   | Type    | Required | Description                                  |
|-------------|---------|----------|----------------------------------------------|
| artist      | string  | no*      | Artist name.                                 |
| album       | string  | no*      | Album name.                                  |
| mbid        | string  | no       | MusicBrainz ID.                              |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.        |

**Returns**

A dictionary containing a list of tags, each with `name`, `count` (number of applications), and `url`.

**Use cases**

- Find out what genres and moods listeners associate with an album.
- Use the tags to discover similar albums via `tag_get_top_albums`.

---

### album_search

Searches Last.fm for albums matching a query string.

**Parameters**

| Parameter | Type    | Required | Description                       |
|-----------|---------|----------|-----------------------------------|
| album     | string  | yes      | Album name to search for.         |
| limit     | integer | no       | Number of results to return.      |
| page      | integer | no       | Page number for paginating results.|

**Returns**

A dictionary containing a list of album results, each with `name`, `artist`, `url`, and image data.

**Use cases**

- Find an album when you are not sure of the exact title.
- Disambiguate between albums with similar names by different artists.

---

## Artist

---

### artist_get_correction

Returns the canonical (corrected) version of an artist name. Last.fm maintains a list of known misspellings and alternate names and maps them to a single canonical form.

**Parameters**

| Parameter | Type   | Required | Description                             |
|-----------|--------|----------|-----------------------------------------|
| artist    | string | yes      | Artist name to check for corrections.  |

**Returns**

A dictionary with the corrected artist name and its Last.fm URL, if a correction exists.

**Use cases**

- Normalize an artist name before passing it to other tools.
- Check whether a name you have is the canonical form Last.fm uses.

---

### artist_get_info

Returns full profile information for an artist. Includes biography text, listener and play counts, similar artists, and top tags.

**Parameters**

| Parameter   | Type    | Required | Description                                                         |
|-------------|---------|----------|---------------------------------------------------------------------|
| artist      | string  | no*      | Artist name.                                                        |
| mbid        | string  | no       | MusicBrainz ID.                                                     |
| lang        | string  | no       | Language for the biography text. ISO 639-1 code, e.g. `en`, `fr`.  |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.                               |
| username    | string  | no       | Include this user's play count for the artist.                      |

**Returns**

A dictionary with fields including:

| Field      | Description                                          |
|------------|------------------------------------------------------|
| name       | Canonical artist name                                |
| listeners  | Total unique listeners on Last.fm                    |
| playcount  | Total plays across all Last.fm users                 |
| bio        | Artist biography (summary and full text)             |
| similar    | List of similar artists                              |
| tags       | Top community tags                                   |
| url        | Last.fm page URL                                     |

**Use cases**

- Read a biography for an artist you are discovering.
- Find similar artists to build a listening queue.
- Check how popular an artist is by listener count.

---

### artist_get_similar

Returns a list of artists similar to the given artist, ranked by similarity score. Similarity is computed from Last.fm's listening data — listeners who play one artist often also play the others.

**Parameters**

| Parameter   | Type    | Required | Description                                       |
|-------------|---------|----------|---------------------------------------------------|
| artist      | string  | no*      | Artist name.                                      |
| mbid        | string  | no       | MusicBrainz ID.                                   |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.             |
| limit       | integer | no       | Maximum number of similar artists to return.      |

**Returns**

A list of artist objects, each with `name`, `match` (similarity score 0–1), and `url`.

**Use cases**

- Find new artists to listen to based on one you already love.
- Build a "you might also like" list for a given artist.

---

### artist_get_tags

Returns the tags a specific user has applied to an artist.

**Parameters**

| Parameter   | Type    | Required | Description                                  |
|-------------|---------|----------|----------------------------------------------|
| artist      | string  | no*      | Artist name.                                 |
| mbid        | string  | no       | MusicBrainz ID.                              |
| user        | string  | no       | The username whose tags to retrieve.         |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.        |

**Returns**

A dictionary containing a list of tag objects with `name` and `url`.

---

### artist_get_top_albums

Returns the most-played albums by an artist on Last.fm, ranked by play count.

**Parameters**

| Parameter   | Type    | Required | Description                              |
|-------------|---------|----------|------------------------------------------|
| artist      | string  | no*      | Artist name.                             |
| mbid        | string  | no       | MusicBrainz ID.                          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.    |
| page        | integer | no       | Page number for pagination.              |
| limit       | integer | no       | Number of results per page.              |

**Returns**

A list of album objects, each with `name`, `playcount`, and `url`.

**Use cases**

- Find out which albums by an artist are most listened to, which is often a good starting point for a new listener.
- Identify an artist's most popular record vs. their full discography.

---

### artist_get_top_tags

Returns the top community tags for an artist, ranked by how many users have applied them.

**Parameters**

| Parameter   | Type    | Required | Description                              |
|-------------|---------|----------|------------------------------------------|
| artist      | string  | no*      | Artist name.                             |
| mbid        | string  | no       | MusicBrainz ID.                          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.    |

**Returns**

A list of tag objects with `name`, `count`, and `url`.

**Use cases**

- Confirm what genre or mood an artist is associated with.
- Pivot to genre exploration using `tag_get_top_artists`.

---

### artist_get_top_tracks

Returns the most-played tracks by an artist on Last.fm, ranked by play count.

**Parameters**

| Parameter   | Type    | Required | Description                              |
|-------------|---------|----------|------------------------------------------|
| artist      | string  | no*      | Artist name.                             |
| mbid        | string  | no       | MusicBrainz ID.                          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.    |
| page        | integer | no       | Page number for pagination.              |
| limit       | integer | no       | Number of results per page.              |

**Returns**

A list of track objects, each with `name`, `playcount`, `listeners`, and `url`.

**Use cases**

- Get the essential tracks for an artist before a deeper listen.
- Find which songs drive the most play activity for an artist.

---

### artist_search

Searches Last.fm for artists matching a query string.

**Parameters**

| Parameter | Type    | Required | Description                        |
|-----------|---------|----------|------------------------------------|
| artist    | string  | yes      | Artist name to search for.         |
| limit     | integer | no       | Number of results to return.       |
| page      | integer | no       | Page number for paginating results.|

**Returns**

A list of artist results, each with `name`, `listeners`, and `url`.

**Use cases**

- Find an artist when you are uncertain of the exact name spelling.
- Discover multiple artists who share a name.

---

## Chart

These tools return the global Last.fm charts — what the entire Last.fm community is listening to most right now.

---

### chart_get_top_artists

Returns the artists with the most listeners globally on Last.fm at this moment.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of artist objects with `name`, `playcount`, `listeners`, and `url`.

---

### chart_get_top_tags

Returns the most-used tags across all of Last.fm right now.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of tag objects with `name`, `reach` (number of listeners using the tag), and `taggings` (total times applied).

---

### chart_get_top_tracks

Returns the tracks with the most listeners globally on Last.fm right now.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of track objects with `name`, `artist`, `playcount`, `listeners`, and `url`.

---

## Geo

These tools return charts filtered by country or city, based on where Last.fm users are located.

---

### geo_get_top_artists

Returns the most popular artists among Last.fm users in a given country.

**Parameters**

| Parameter | Type    | Required | Description                                         |
|-----------|---------|----------|-----------------------------------------------------|
| country   | string  | yes      | Country name in English, e.g. `Germany`, `Japan`.   |
| page      | integer | no       | Page number for pagination.                         |
| limit     | integer | no       | Number of results per page.                         |

**Returns**

A list of artist objects with `name`, `listeners`, and `url`.

**Use cases**

- Discover what music is popular in a specific country.
- Research regional music tastes for travel or cultural interest.

---

### geo_get_top_tracks

Returns the most popular tracks among Last.fm users in a given country, optionally narrowed to a specific city or metro area.

**Parameters**

| Parameter | Type    | Required | Description                                                               |
|-----------|---------|----------|---------------------------------------------------------------------------|
| country   | string  | yes      | Country name in English, e.g. `United Kingdom`.                           |
| location  | string  | no       | City or metro name within the country, e.g. `London`, `Manchester`.       |
| page      | integer | no       | Page number for pagination.                                               |
| limit     | integer | no       | Number of results per page.                                               |

**Returns**

A list of track objects with `name`, `artist`, `listeners`, and `url`.

**Use cases**

- Find out what is trending in a specific city.
- Compare national vs. local music tastes.

---

## Library

---

### library_get_artists

Returns all artists in a user's Last.fm library, along with their play counts and scrobble frequency for that user.

**Parameters**

| Parameter | Type    | Required | Description                          |
|-----------|---------|----------|--------------------------------------|
| user      | string  | yes      | Username whose library to retrieve.  |
| page      | integer | no       | Page number for pagination.          |
| limit     | integer | no       | Number of results per page.          |

**Returns**

A list of artist objects with `name`, `playcount`, `tagcount`, and `url`.

**Use cases**

- Browse the full artist catalog a user has ever listened to.
- Find artists in a user's library that are not visible in their top artists (which only shows a limited period).

> **Library vs. top artists:** A user's library contains every artist they have ever scrobbled, regardless of when. Top artists tools (`user_get_top_artists`) show rankings for a specific time window (like the last 7 days or year). The library is cumulative.

---

## Tag

Tags on Last.fm are global. Any listener can apply any tag to any artist, album, or track. The tags below represent community consensus across millions of listeners.

---

### tag_get_info

Returns metadata and a wiki description for a tag.

**Parameters**

| Parameter | Type   | Required | Description                                              |
|-----------|--------|----------|----------------------------------------------------------|
| tag       | string | yes      | Tag name, e.g. `shoegaze`, `jazz`, `workout`.            |
| lang      | string | no       | Language for wiki content. ISO 639-1 code, e.g. `en`.   |

**Returns**

A dictionary with `name`, `reach`, `total` (total taggings), and `wiki` (description text).

---

### tag_get_similar

Returns tags that are similar to a given tag, based on how often they are applied to the same artists and tracks.

**Parameters**

| Parameter | Type   | Required | Description         |
|-----------|--------|----------|---------------------|
| tag       | string | yes      | Tag name to match.  |

**Returns**

A list of tag names.

**Use cases**

- Find related genre tags to broaden a search.
- Explore adjacent moods and subgenres.

---

### tag_get_top_albums

Returns the albums most associated with a given tag, ranked by tag strength.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| tag       | string  | yes      | Tag name.                    |
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of album objects with `name`, `artist`, and `url`.

**Use cases**

- Find essential albums in a genre or mood category.
- Build a listening list for an unfamiliar style, e.g. `post-rock` or `bossa nova`.

---

### tag_get_top_artists

Returns the artists most associated with a given tag.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| tag       | string  | yes      | Tag name.                    |
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of artist objects with `name` and `url`.

**Use cases**

- Discover artists in a genre or mood you enjoy.
- Find the most representative artists for a tag before exploring its top albums.

---

### tag_get_top_tags

Returns the most widely used tags across all of Last.fm. No parameters required — this is a global snapshot.

**Parameters**

None.

**Returns**

A list of tag objects with `name`, `count`, and `reach`.

**Use cases**

- Browse the most popular genres and moods on Last.fm.
- Find tag names to pass to other tag tools.

---

### tag_get_top_tracks

Returns the tracks most associated with a given tag.

**Parameters**

| Parameter | Type    | Required | Description                  |
|-----------|---------|----------|------------------------------|
| tag       | string  | yes      | Tag name.                    |
| page      | integer | no       | Page number for pagination.  |
| limit     | integer | no       | Number of results per page.  |

**Returns**

A list of track objects with `name`, `artist`, and `url`.

**Use cases**

- Get representative tracks for a genre or mood.
- Build a sampler playlist for a tag you want to explore.

---

### tag_get_weekly_chart_list

Returns the list of available weekly date ranges for a tag's chart history. Use these timestamps with weekly chart tools.

**Parameters**

| Parameter | Type   | Required | Description  |
|-----------|--------|----------|--------------|
| tag       | string | yes      | Tag name.    |

**Returns**

A list of objects, each with `from` and `to` Unix timestamps representing a week boundary.

---

## Track

---

### track_get_correction

Returns the canonical corrected version of a track name. Useful when you have a track name from an external source that may be a variant spelling.

**Parameters**

| Parameter | Type   | Required | Description        |
|-----------|--------|----------|--------------------|
| artist    | string | yes      | Artist name.       |
| track     | string | yes      | Track name.        |

**Returns**

A dictionary with the corrected artist and track names and the Last.fm URL.

---

### track_get_info

Returns detailed information for a track. Includes duration, play count, listener count, album membership, and wiki text when available.

**Parameters**

| Parameter   | Type    | Required | Description                                                       |
|-------------|---------|----------|-------------------------------------------------------------------|
| artist      | string  | no*      | Artist name.                                                      |
| track       | string  | no*      | Track name.                                                       |
| mbid        | string  | no       | MusicBrainz ID.                                                   |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.                             |
| username    | string  | no       | Include this user's play count for the track in the response.     |

**Returns**

A dictionary with fields including:

| Field     | Description                                      |
|-----------|--------------------------------------------------|
| name      | Track title                                      |
| artist    | Artist name                                      |
| album     | Album the track belongs to (if known)            |
| duration  | Duration in milliseconds                         |
| listeners | Total unique listeners                           |
| playcount | Total plays across all Last.fm users             |
| toptags   | Top community tags for this track                |
| wiki      | Description or annotation text (if available)    |
| url       | Last.fm page URL                                 |

---

### track_get_similar

Returns tracks that are similar to a given track, based on Last.fm listening patterns.

**Parameters**

| Parameter   | Type    | Required | Description                              |
|-------------|---------|----------|------------------------------------------|
| artist      | string  | no*      | Artist name.                             |
| track       | string  | no*      | Track name.                              |
| mbid        | string  | no       | MusicBrainz ID.                          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.    |
| limit       | integer | no       | Maximum number of similar tracks.        |

**Returns**

A list of track objects with `name`, `artist`, `match` (similarity score 0–1), and `url`.

**Use cases**

- Find tracks to follow a song you just heard.
- Build a playlist of songs with a similar feel to a specific track.

---

### track_get_tags

Returns the tags a specific user has applied to a track.

**Parameters**

| Parameter   | Type    | Required | Description                                   |
|-------------|---------|----------|-----------------------------------------------|
| artist      | string  | no*      | Artist name.                                  |
| track       | string  | no*      | Track name.                                   |
| mbid        | string  | no       | MusicBrainz ID.                               |
| user        | string  | no       | The username whose tags to retrieve.          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.         |

**Returns**

A list of tag objects with `name` and `url`.

---

### track_get_top_tags

Returns the top community tags for a track.

**Parameters**

| Parameter   | Type    | Required | Description                              |
|-------------|---------|----------|------------------------------------------|
| artist      | string  | no*      | Artist name.                             |
| track       | string  | no*      | Track name.                              |
| mbid        | string  | no       | MusicBrainz ID.                          |
| autocorrect | integer | no       | Pass `1` to correct misspelled names.    |

**Returns**

A list of tag objects with `name`, `count`, and `url`.

---

### track_search

Searches Last.fm for tracks matching a query string. You can optionally filter by artist name to narrow results.

**Parameters**

| Parameter | Type    | Required | Description                                         |
|-----------|---------|----------|-----------------------------------------------------|
| track     | string  | yes      | Track name to search for.                           |
| artist    | string  | no       | Artist name to filter results by.                   |
| limit     | integer | no       | Number of results to return.                        |
| page      | integer | no       | Page number for paginating results.                 |

**Returns**

A list of track results, each with `name`, `artist`, `listeners`, and `url`.

---

## User

User tools return data from individual Last.fm profiles. Most require only a public username — no authentication is needed to read someone's listening history if their profile is public.

---

### user_get_friends

Returns a user's friends on Last.fm.

**Parameters**

| Parameter     | Type    | Required | Description                                                    |
|---------------|---------|----------|----------------------------------------------------------------|
| user          | string  | yes      | Username.                                                      |
| recent_tracks | boolean | no       | If `true`, include the most recent track for each friend.      |
| page          | integer | no       | Page number for pagination.                                    |
| limit         | integer | no       | Number of results per page.                                    |

**Returns**

A list of user objects with profile fields and optionally the most recently played track.

---

### user_get_info

Returns profile information for a Last.fm user.

**Parameters**

| Parameter | Type   | Required | Description                  |
|-----------|--------|----------|------------------------------|
| user      | string | no       | Username to look up.         |

**Returns**

A dictionary with fields including:

| Field       | Description                                     |
|-------------|-------------------------------------------------|
| name        | Username                                        |
| realname    | Display name (if set)                           |
| country     | Country (if set)                                |
| age         | Age (if set)                                    |
| playcount   | Total tracks scrobbled                          |
| playlists   | Number of playlists                             |
| registered  | Account registration date                       |
| url         | Last.fm profile URL                             |
| image       | Profile image URLs                              |

**Use cases**

- Check how long someone has been on Last.fm and how many scrobbles they have.
- Get the profile URL to link to a user's page.

---

### user_get_loved_tracks

Returns the tracks a user has marked as loved on Last.fm.

**Parameters**

| Parameter | Type    | Required | Description                         |
|-----------|---------|----------|-------------------------------------|
| user      | string  | yes      | Username.                           |
| page      | integer | no       | Page number for pagination.         |
| limit     | integer | no       | Number of results per page.         |

**Returns**

A list of track objects with `name`, `artist`, the date the track was loved, and `url`.

**Use cases**

- See a user's personal list of favorite tracks.
- Use loved tracks as seed material for music recommendations.

---

### user_get_personal_tags

Returns the items a user has tagged with a specific personal tag, grouped by type.

**Parameters**

| Parameter    | Type   | Required | Description                                              |
|--------------|--------|----------|----------------------------------------------------------|
| user         | string | yes      | Username.                                                |
| tag          | string | yes      | The personal tag to retrieve items for.                  |
| tagging_type | string | yes      | Type of items: `artist`, `album`, or `track`.            |

**Returns**

A list of artist, album, or track objects depending on `tagging_type`.

**Use cases**

- Retrieve everything a user has tagged with a personal label like `favorites` or `road trip`.

---

### user_get_recent_tracks

Returns the tracks a user has most recently scrobbled, in reverse chronological order. The currently playing track (if any) appears at the top with a `nowplaying` flag.

**Parameters**

| Parameter      | Type    | Required | Description                                              |
|----------------|---------|----------|----------------------------------------------------------|
| user           | string  | yes      | Username.                                                |
| page           | integer | no       | Page number for pagination.                              |
| limit          | integer | no       | Number of results per page (max 200 per request).        |
| from_timestamp | integer | no       | Unix timestamp — only return scrobbles after this time.  |
| to_timestamp   | integer | no       | Unix timestamp — only return scrobbles before this time. |

**Returns**

A list of track objects with `name`, `artist`, `album`, `date` (scrobble timestamp), and `url`. The most recent entry may include `nowplaying: true`.

**Use cases**

- See what someone is listening to right now.
- Review a user's recent listening session.
- Retrieve scrobbles from a specific time window using the timestamp parameters.

> **What is scrobbling?** Scrobbling is the act of recording a track play to Last.fm. When your music player (Spotify, Apple Music, a media player with a plugin, etc.) sends a track play to Last.fm, that is called a scrobble. The term comes from Last.fm's original name: Audioscrobbler.

---

### user_get_top_albums

Returns a user's most-played albums over a given time period.

**Parameters**

| Parameter | Type    | Required | Description                                                              |
|-----------|---------|----------|--------------------------------------------------------------------------|
| user      | string  | yes      | Username.                                                                |
| period    | string  | no       | Time window. One of: `overall`, `7day`, `1month`, `3month`, `6month`, `12month`. |
| page      | integer | no       | Page number for pagination.                                              |
| limit     | integer | no       | Number of results per page.                                              |

**Returns**

A list of album objects with `name`, `artist`, `playcount`, and `url`.

---

### user_get_top_artists

Returns a user's most-played artists over a given time period.

**Parameters**

| Parameter | Type    | Required | Description                                                              |
|-----------|---------|----------|--------------------------------------------------------------------------|
| user      | string  | yes      | Username.                                                                |
| period    | string  | no       | Time window. One of: `overall`, `7day`, `1month`, `3month`, `6month`, `12month`. |
| page      | integer | no       | Page number for pagination.                                              |
| limit     | integer | no       | Number of results per page.                                              |

**Returns**

A list of artist objects with `name`, `playcount`, and `url`.

---

### user_get_top_tags

Returns the tags a user applies most frequently in their library.

**Parameters**

| Parameter | Type   | Required | Description  |
|-----------|--------|----------|--------------|
| user      | string | yes      | Username.    |

**Returns**

A list of tag objects with `name`, `count`, and `url`.

**Use cases**

- Understand how a user self-categorizes their music taste.
- Use the top tags to seed genre-based discovery tools.

---

### user_get_top_tracks

Returns a user's most-played tracks over a given time period.

**Parameters**

| Parameter | Type    | Required | Description                                                              |
|-----------|---------|----------|--------------------------------------------------------------------------|
| user      | string  | yes      | Username.                                                                |
| period    | string  | no       | Time window. One of: `overall`, `7day`, `1month`, `3month`, `6month`, `12month`. |
| page      | integer | no       | Page number for pagination.                                              |
| limit     | integer | no       | Number of results per page.                                              |

**Returns**

A list of track objects with `name`, `artist`, `playcount`, and `url`.

---

### user_get_weekly_album_chart

Returns a user's most-played albums during a specific week.

**Parameters**

| Parameter      | Type    | Required | Description                                                       |
|----------------|---------|----------|-------------------------------------------------------------------|
| user           | string  | yes      | Username.                                                         |
| from_timestamp | integer | no       | Unix timestamp for the start of the week.                         |
| to_timestamp   | integer | no       | Unix timestamp for the end of the week.                           |

If you omit both timestamps, Last.fm returns the most recent available week. To retrieve a specific historical week, use timestamps from `user_get_weekly_chart_list`.

**Returns**

A list of album objects with `name`, `artist`, `playcount`, and `mbid`.

---

### user_get_weekly_artist_chart

Returns a user's most-played artists during a specific week.

**Parameters**

| Parameter      | Type    | Required | Description                                  |
|----------------|---------|----------|----------------------------------------------|
| user           | string  | yes      | Username.                                    |
| from_timestamp | integer | no       | Unix timestamp for the start of the week.    |
| to_timestamp   | integer | no       | Unix timestamp for the end of the week.      |

**Returns**

A list of artist objects with `name`, `playcount`, and `mbid`.

---

### user_get_weekly_chart_list

Returns the list of all available weekly date ranges for a user's chart history, from account creation to the present. Use the `from` and `to` values from these ranges with the weekly chart tools.

**Parameters**

| Parameter | Type   | Required | Description  |
|-----------|--------|----------|--------------|
| user      | string | yes      | Username.    |

**Returns**

A list of objects, each with `from` and `to` Unix timestamps.

**Use cases**

- Find the timestamp pair for a specific week to pass to a weekly chart tool.
- Determine the full span of a user's listening history.

---

### user_get_weekly_track_chart

Returns a user's most-played tracks during a specific week.

**Parameters**

| Parameter      | Type    | Required | Description                                  |
|----------------|---------|----------|----------------------------------------------|
| user           | string  | yes      | Username.                                    |
| from_timestamp | integer | no       | Unix timestamp for the start of the week.    |
| to_timestamp   | integer | no       | Unix timestamp for the end of the week.      |

**Returns**

A list of track objects with `name`, `artist`, `playcount`, and `mbid`.
