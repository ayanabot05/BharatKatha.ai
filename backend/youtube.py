"""Read-only YouTube popularity chart. Uses the official Data API, not page scraping."""
import html
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

_cached = {}
_names = {"hi": "Hindi", "bn": "Bengali", "mr": "Marathi", "te": "Telugu", "ta": "Tamil",
          "gu": "Gujarati", "ur": "Urdu", "kn": "Kannada", "or": "Odia", "ml": "Malayalam", "en": "English"}
_scripts = {"hi": (0x0900, 0x097F), "mr": (0x0900, 0x097F), "bn": (0x0980, 0x09FF),
            "gu": (0x0A80, 0x0AFF), "or": (0x0B00, 0x0B7F), "ta": (0x0B80, 0x0BFF),
            "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF), "ml": (0x0D00, 0x0D7F),
            "ur": (0x0600, 0x06FF)}
_topics = {"Moral stories": "moral story", "Village life": "village life story",
           "Mythology & Puranas": "mythology story", "Kids stories": "kids story",
           "Love & family drama": "family drama story", "Mystery": "mystery story",
           "Motivation": "motivational story", "Animal fables": "animal story",
           "Comedy": "comedy story"}


def _rank(video, language, region, category, audience):
    title = video["title"].lower()
    bounds = _scripts.get(language)
    native = bool(bounds and any(bounds[0] <= ord(c) <= bounds[1] for c in title))
    tagged = (video.get("language") or "").lower().split("-")[0] == language
    named = _names[language].lower() in title
    topic_words = [w for w in _topics[category].split() if len(w) > 3]
    region_words = [w for w in region.lower().split() if len(w) > 3]
    audience_words = [w for w in audience.lower().split() if len(w) > 3]
    return (3 * native + tagged + 2 * named + 2 * sum(w in title for w in topic_words)
            + sum(w in title for w in region_words) + sum(w in title for w in audience_words)
            + math.log10(video["views"] + 1) / 3)


async def relevant_india(language="te", region="Andhra Pradesh", category="Moral stories",
                         audience="Families & kids"):
    """Recent short-video search; language and region are relevance hints, not verified trends."""
    language = language if language in _names else "te"
    category = category if category in _topics else "Moral stories"
    region = re.sub(r"\s+", " ", region.strip())[:60]
    audience = re.sub(r"\s+", " ", audience.strip())[:60]
    cache_key = (language, region.casefold(), category, audience.casefold())
    cached = _cached.get(cache_key)
    if cached and time.time() - cached[0] < 21600:
        return cached[1]
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("YouTube discovery needs YOUTUBE_API_KEY configured on the server")
    query = f"{_names[language]} {_topics[category]} shorts"
    if category == "Village life" and region:
        query += f" {region}"
    if "kid" in audience.lower() and category not in ("Kids stories", "Moral stories"):
        query += " kids"
    after = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds").replace("+00:00", "Z")
    async with httpx.AsyncClient(timeout=20) as client:
        search = await client.get("https://www.googleapis.com/youtube/v3/search", params={
            "key": key, "part": "snippet", "q": query, "type": "video", "videoDuration": "short",
            "regionCode": "IN", "relevanceLanguage": language, "publishedAfter": after,
            "order": "viewCount", "safeSearch": "moderate", "maxResults": 25,
        })
        if search.status_code != 200:
            raise RuntimeError(f"YouTube discovery unavailable ({search.status_code}); check API access and quota")
        ids = [item.get("id", {}).get("videoId") for item in search.json().get("items", [])]
        ids = [id for id in ids if id]
        if not ids:
            result = {"items": [], "note": "No recent short videos matched this selection. Try a broader category."}
            _cached[cache_key] = (time.time(), result)
            return result
        details = await client.get("https://www.googleapis.com/youtube/v3/videos", params={
            "key": key, "part": "snippet,statistics", "id": ",".join(ids), "maxResults": 25,
        })
        if details.status_code != 200:
            raise RuntimeError(f"YouTube video details unavailable ({details.status_code})")
    items = []
    for video in details.json().get("items", []):
        snippet = video.get("snippet") or {}
        stats = video.get("statistics") or {}
        items.append({"id": video.get("id"), "title": html.unescape(snippet.get("title", "")),
                      "channel": html.unescape(snippet.get("channelTitle", "")),
                      "published_at": snippet.get("publishedAt"),
                      "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                      "views": int(stats.get("viewCount") or 0),
                      "thumbnail": (snippet.get("thumbnails") or {}).get("medium", {}).get("url"),
                      "url": f"https://www.youtube.com/watch?v={video.get('id')}"})
    items.sort(key=lambda video: _rank(video, language, region, category, audience), reverse=True)
    result = {"items": items[:12],
              "note": "Recent India-viewable short videos (last 30 days), ranked by topic, language clues and views. "
                      "YouTube does not verify spoken language or provide state-level trends; use these only for inspiration."}
    _cached[cache_key] = (time.time(), result)
    return result


async def popular_india():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("YouTube trends need YOUTUBE_API_KEY configured on the server")
    cached = _cached.get("IN")
    if cached and time.time() - cached[0] < 3600:
        return cached[1]
    params = {"key": key, "part": "snippet,statistics", "chart": "mostPopular", "regionCode": "IN",
              "maxResults": 25}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://www.googleapis.com/youtube/v3/videos", params=params)
    if response.status_code != 200:
        raise RuntimeError(f"YouTube chart unavailable ({response.status_code}); check API access and quota")
    items = []
    for video in response.json().get("items", []):
        snippet = video.get("snippet") or {}
        stats = video.get("statistics") or {}
        items.append({"id": video.get("id"), "title": snippet.get("title", ""),
                      "channel": snippet.get("channelTitle", ""), "published_at": snippet.get("publishedAt"),
                      "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                      "views": int(stats.get("viewCount") or 0),
                      "thumbnail": (snippet.get("thumbnails") or {}).get("medium", {}).get("url"),
                      "url": f"https://www.youtube.com/watch?v={video.get('id')}"})
    _cached["IN"] = (time.time(), items)
    return items
