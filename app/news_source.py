import feedparser

from .config import RSS_FEEDS
from .storage import is_source_processed


def _split_source(title: str, entry: dict) -> tuple[str, str]:
    """Google News RSS titles come as "Headline - Publisher", and entries
    also carry a <source> tag with the publisher name - use whichever gives
    a clean answer to separate the two, so the headline shown to the script
    generator isn't polluted with the trailing publisher name, and the
    publisher is available on its own for the on-screen source citation."""
    source = entry.get("source")
    source_name = (source.get("title") if isinstance(source, dict) else "") or ""
    if source_name and title.endswith(f" - {source_name}"):
        return title[: -(len(source_name) + 3)].strip(), source_name
    if " - " in title:
        headline, _, tail = title.rpartition(" - ")
        return headline.strip(), tail.strip()
    return title.strip(), source_name


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
            title, source_name = _split_source(entry.get("title", "").strip(), entry)
            candidates.append(
                {
                    "title": title,
                    "summary": entry.get("summary", "").strip(),
                    "link": link,
                    "published": entry.get("published", ""),
                    "source_name": source_name,
                }
            )
            if len(candidates) >= limit:
                return candidates
    return candidates
