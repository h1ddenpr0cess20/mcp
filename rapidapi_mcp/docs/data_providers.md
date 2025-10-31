# Upstream Data Providers

The FastMCP integrations are thin wrappers around RapidAPI hosts. Every tool in
this repository talks to exactly one of the subscriptions listed below. Make
sure your RapidAPI account is subscribed before turning on a domain server, or
the requests will fail with authentication errors.

| API | Domain(s) | What it Delivers | RapidAPI Listing |
| --- | --------- | ---------------- | ---------------- |
| IMDB8 | Entertainment | Film, television, and cast metadata for search and lookup prompts. | https://rapidapi.com/apidojo/api/imdb8 |
| Steam2 | Entertainment | Steam catalog and pricing details for PC game discovery. | https://rapidapi.com/psimavel/api/steam2 |
| Spotify23 | Entertainment | Track, album, and artist search to drive music-focused flows. | https://rapidapi.com/Glavier/api/spotify23 |
| Real-Time News Data | News | Headlines and breaking-news summaries from multiple outlets. | https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-news-data |
| Real-Time Web Search | Search | General-purpose web search results with snippets and source metadata. | https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-web-search |
| Local Business Data | Realestate, Finance, Search | Geolocated business listings, contact info, and category tags. | https://rapidapi.com/letscrape-6bRBa3QguO5/api/local-business-data |
| Tasty | Food | Recipe search, including ingredients and instructions. | https://rapidapi.com/apidojo/api/tasty |
| Twitter154 (The Old Bird) | Social | Public social posts and profile data for monitoring feeds. | https://rapidapi.com/datahungrybeast/api/twitter154 |
| Zillow (zillow-com4) | Realestate | Property listings, valuation data, and rental insights. | https://rapidapi.com/Glavier/api/zillow-com4 |
| JSearch | Jobs | Job posting aggregation with filters for location, seniority, and more. | https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch |

## Operational Checklist

1. Verify `RAPIDAPI_KEY` has access to every subscription you intend to use.
2. Subscribe to free tiers during development; upgrade before production loads.
3. Track rate limits—every API above enforces its own quotas. The wrappers do
   not retry automatically.

> Tip: capture the subscription tier and known limits in your team wiki if you
> expect heavy traffic so future operators do not have to rediscover them.
