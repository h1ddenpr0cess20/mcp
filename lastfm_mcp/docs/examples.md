# Usage Examples

Practical workflows showing how to combine tools for common music tasks. Each scenario includes the sequence of tool calls and sample questions you can ask an AI assistant connected to this server.

---

## Table of Contents

- [Discover an Artist You Have Never Heard](#discover-an-artist-you-have-never-heard)
- [Find Music in a Genre or Mood](#find-music-in-a-genre-or-mood)
- [Analyze Your Own Listening History](#analyze-your-own-listening-history)
- [Build a Playlist from a Starting Track](#build-a-playlist-from-a-starting-track)
- [Explore What Is Trending](#explore-what-is-trending)
- [Research an Album Before Listening](#research-an-album-before-listening)
- [Compare Two Artists](#compare-two-artists)
- [Dig Into a Friend's Music Taste](#dig-into-a-friends-music-taste)
- [Explore Regional Music](#explore-regional-music)
- [Weekly Listening Review](#weekly-listening-review)
- [Sample Questions for an AI Assistant](#sample-questions-for-an-ai-assistant)

---

## Discover an Artist You Have Never Heard

**Goal:** Get a complete introduction to an unfamiliar artist — who they are, what they sound like, and where to start listening.

**Tool sequence:**

1. `artist_get_info` — biography, listener count, and top tags (genre/mood)
2. `artist_get_top_tracks` — their most-played songs, a good entry point
3. `artist_get_top_albums` — which records have the broadest listener base
4. `artist_get_similar` — other artists you might already know who are similar

**Why this order:** Start with context (who are they, what genre), then find the songs and albums that represent them best. Similar artists let you cross-reference against things you already know.

**Sample prompts to an AI assistant:**

> Tell me about Grouper. Who are they, what genre are they, and what should I listen to first?

> I just heard of Khruangbin. Give me a full introduction — their sound, their most popular tracks, and who else I might enjoy.

> What artists are similar to Four Tet, and what are Four Tet's most-played tracks?

---

## Find Music in a Genre or Mood

**Goal:** Start from a genre tag or mood and find the artists, albums, and tracks most associated with it.

**Tool sequence:**

1. `tag_get_info` — confirm the tag exists and read a description of what it means
2. `tag_get_top_artists` — the most representative artists for this tag
3. `tag_get_top_albums` — the most listened-to albums in this genre
4. `tag_get_top_tracks` — individual tracks to sample the sound
5. `tag_get_similar` — related tags to broaden or refocus the search

**Sample prompts to an AI assistant:**

> I want to explore shoegaze. Who are the most listened-to shoegaze artists on Last.fm, and what are the essential albums?

> Give me the top artists and albums tagged as "dark ambient."

> What tags are similar to "indie folk"? I want to find related genres I might enjoy.

> Find me the top tracks tagged as "melancholy" — I want something mellow for studying.

**Tips:**

- Tag names on Last.fm are lowercase and often hyphenated: `post-rock`, `singer-songwriter`, `lo-fi`.
- Very specific tags often work: `female fronted metal`, `80s new wave`, `japanese city pop`.
- If `tag_get_info` returns no wiki content, the tag exists but has no description — it is still usable with the other tag tools.

---

## Analyze Your Own Listening History

**Goal:** Review what you have been listening to and identify patterns in your music taste.

**Tool sequence:**

1. `user_get_info` — basic profile stats including total scrobble count
2. `user_get_top_artists` with `period="7day"` — what you played most this week
3. `user_get_top_artists` with `period="overall"` — your all-time most-played artists
4. `user_get_top_tracks` with `period="1month"` — tracks you have had on repeat this month
5. `user_get_top_tags` — the genre tags that define your library
6. `user_get_recent_tracks` — your most recent listening session

**Sample prompts to an AI assistant:**

> Analyze the listening history for Last.fm user "yourusername." What have I been playing most this week vs. all time?

> What genres dominate my Last.fm library? Check my top tags and explain what they mean.

> What were my most-played albums last month?

> What was the last thing I listened to on Last.fm?

> How does my listening this week compare to my all-time favorites?

---

## Build a Playlist from a Starting Track

**Goal:** Take one track you love and find similar tracks to build around it.

**Tool sequence:**

1. `track_get_info` — confirm the track details and see its top tags
2. `track_get_similar` — tracks Last.fm considers sonically similar
3. `track_get_top_tags` — use the tags to pivot to `tag_get_top_tracks` for more options
4. `artist_get_similar` — find similar artists, then pull their top tracks

**Sample prompts to an AI assistant:**

> I love "Teardrop" by Massive Attack. Find me 10 similar tracks I can build a playlist around.

> Build a playlist starting from "Motion Picture Soundtrack" by Radiohead. What tracks have a similar feel?

> What artists are similar to Beach House, and what are their most popular tracks? I want to extend a playlist I'm building.

**Tips:**

- `track_get_similar` is based on listening co-occurrence, not musical analysis — results can be surprising and occasionally off-genre, but they often surface hidden gems.
- Combining similar tracks with similar artists gives a fuller result set than either tool alone.

---

## Explore What Is Trending

**Goal:** See what the global Last.fm community is listening to right now.

**Tool sequence:**

1. `chart_get_top_artists` — the most popular artists globally at this moment
2. `chart_get_top_tracks` — the most-played tracks globally
3. `chart_get_top_tags` — the genres and moods that are most active
4. `tag_get_top_artists` on a trending tag — dive into what is driving a genre spike

**Sample prompts to an AI assistant:**

> What are the most listened-to artists on Last.fm right now?

> What are the global top tracks on Last.fm today?

> What genres are trending on Last.fm? Show me the top tags and the artists driving them.

---

## Research an Album Before Listening

**Goal:** Get enough information about an album to decide whether it is worth your time and understand its context.

**Tool sequence:**

1. `album_get_info` — track listing, play count, wiki summary, and release info
2. `album_get_top_tags` — community tags confirming genre and mood
3. `artist_get_info` — background on the artist making the album
4. `artist_get_top_albums` — where this album sits in the artist's catalog by popularity

**Sample prompts to an AI assistant:**

> Tell me about "In the Aeroplane Over the Sea" by Neutral Milk Hotel. What is on it and what do listeners say about it?

> I'm thinking of listening to "Bitches Brew" by Miles Davis. What genre is it, and where does it sit in his catalog?

> Give me a full rundown on "OK Computer" by Radiohead — the track list, the tags, and a summary.

---

## Compare Two Artists

**Goal:** Side-by-side comparison of two artists to understand how they relate.

**Tool sequence (run for each artist):**

1. `artist_get_info` — listener counts and biography
2. `artist_get_top_tags` — their respective genre tags
3. `artist_get_top_tracks` — most popular songs for each
4. `artist_get_similar` — check whether either appears in the other's similar artists list

**Sample prompts to an AI assistant:**

> Compare the Cure and Depeche Mode. Which has more listeners on Last.fm, what genres do they each occupy, and do they share similar artists?

> Who is more popular on Last.fm — Aphex Twin or Boards of Canada? Show me their listener counts and top tags.

> I can't decide between two artists to get into: Prefab Sprout or The Blue Nile. Compare them and help me understand the difference.

---

## Dig Into a Friend's Music Taste

**Goal:** Understand what a friend listens to and find recommendations to share with them.

**Tool sequence:**

1. `user_get_info` — their profile stats and scrobble count
2. `user_get_top_artists` with `period="overall"` — their all-time favorite artists
3. `user_get_top_tags` — the genres that define their taste
4. `user_get_loved_tracks` — their personally curated favorites list
5. `artist_get_similar` on one of their top artists — find artists they might not know yet

**Sample prompts to an AI assistant:**

> My friend's Last.fm username is "friendusername." What kind of music do they listen to?

> Based on the top artists in my friend's Last.fm profile, what artist might they enjoy that is not in their library yet?

> What tracks has "friendusername" loved on Last.fm? I want to get a feel for their taste before making a recommendation.

---

## Explore Regional Music

**Goal:** Discover what music is popular in a specific country or city.

**Tool sequence:**

1. `geo_get_top_artists` — most popular artists in a country
2. `geo_get_top_tracks` — most popular tracks, optionally in a specific city
3. `artist_get_info` on one of the results — learn more about an unfamiliar regional artist

**Sample prompts to an AI assistant:**

> What artists are most popular in Brazil on Last.fm?

> What are the top tracks in Japan right now on Last.fm?

> What music is trending in Berlin? Use Germany as the country and Berlin as the location.

> Who are the most popular artists in South Korea on Last.fm?

---

## Weekly Listening Review

**Goal:** Pull a detailed breakdown of what you listened to during a specific week.

**Tool sequence:**

1. `user_get_weekly_chart_list` — get the available weekly date ranges
2. `user_get_weekly_artist_chart` with the desired week's timestamps — top artists that week
3. `user_get_weekly_track_chart` with the same timestamps — top tracks that week
4. `user_get_weekly_album_chart` with the same timestamps — top albums that week

**Sample prompts to an AI assistant:**

> What were my top artists, albums, and tracks on Last.fm last week?

> Pull the available weekly chart history for my Last.fm account and show me what I played most during the most recent week.

> Give me a listening report for a specific week — I want to see all three charts: artists, tracks, and albums.

> **Note:** The weekly chart tools use Unix timestamps. Ask the AI assistant to handle this conversion for you — it can retrieve the list of available weeks and select the one you want.

---

## Sample Questions for an AI Assistant

The following questions show what you can ask an AI assistant that has this MCP server connected. Each maps to one or more tool calls the assistant will make on your behalf.

**Artist discovery**
- Who is Nick Drake and what should I listen to first?
- What artists are similar to Portishead?
- Tell me about the band Godspeed You! Black Emperor.
- What are the most popular tracks by Bjork on Last.fm?

**Genre and mood exploration**
- What are the top artists tagged as "dream pop"?
- Find me the best albums tagged as "jazz fusion."
- What genres are similar to "trip hop"?
- Show me the top tracks tagged as "rainy day."
- What does the "krautrock" tag mean and who are the key artists?

**My listening history** (replace "yourusername" with your own username)
- What have I been playing most on Last.fm this week?
- What are my all-time top artists on Last.fm?
- What tracks have I loved on Last.fm?
- What genres define my Last.fm library?
- Show me my recent scrobbles.

**Album research**
- What is on "Blue" by Joni Mitchell?
- Tell me about "Loveless" by My Bloody Valentine — what genre is it and how popular is it?
- Where does "Kid A" sit in Radiohead's catalog by listener count?

**Charts and trends**
- What are the most popular artists on Last.fm globally right now?
- What is trending in France on Last.fm?
- What genres are most active on Last.fm today?

**Playlist building**
- Find tracks similar to "Halah" by Mazzy Star.
- I love "Don't Look Back in Anger" by Oasis. What similar tracks can I queue up?
- Give me a playlist of tracks in the style of early Boards of Canada.

**Track and album info**
- How long is "Echoes" by Pink Floyd?
- How many people have listened to "Bohemian Rhapsody" on Last.fm?
- What are the top tags for the album "Dummy" by Portishead?
