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


def _feed_items(feed_url: str) -> list[dict]:
    items = []
    for entry in feedparser.parse(feed_url).entries:
        link = entry.get("link")
        if not link or is_source_processed(link):
            continue
        title, source_name = _split_source(entry.get("title", "").strip(), entry)
        items.append(
            {
                "title": title,
                "summary": entry.get("summary", "").strip(),
                "link": link,
                "published": entry.get("published", ""),
                "source_name": source_name,
            }
        )
    return items


def fetch_candidate_news(limit: int = 5) -> list[dict]:
    """Returns up to `limit` unprocessed news items, taking them from the
    configured feeds in turn rather than draining the first one.

    Draining mattered: the old version walked the feeds in order and
    returned as soon as it had enough, so the first feed supplied every
    candidate and any feed after it was dead config - adding a second
    source would have changed nothing at all."""
    per_feed = [_feed_items(feed_url) for feed_url in RSS_FEEDS]

    candidates: list[dict] = []
    for index in range(max((len(items) for items in per_feed), default=0)):
        for items in per_feed:
            if index < len(items):
                candidates.append(items[index])
                if len(candidates) >= limit:
                    return candidates
    return candidates
