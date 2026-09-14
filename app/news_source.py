import feedparser

from .config import RSS_FEEDS
from .storage import is_source_processed


def fetch_candidate_news(limit: int = 5) -> list[dict]:
    """Returns up to `limit` news items from the configured RSS feeds that
    have not been turned into a video yet."""
    candidates = []
    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link")
            if not link or is_source_processed(link):
                continue
            candidates.append(
                {
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", "").strip(),
                    "link": link,
                    "published": entry.get("published", ""),
                }
            )
            if len(candidates) >= limit:
                return candidates
    return candidates
