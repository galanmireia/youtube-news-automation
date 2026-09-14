import re
import unicodedata

import feedparser

from .config import RSS_FEEDS
from .storage import is_source_processed, recent_processed_titles

# Two headlines sharing this much of their vocabulary are the same story.
# Set by hand rather than tuned: outlets rewrite the wording but keep the
# names and the key nouns, which is most of a short headline.
_SAME_STORY_OVERLAP = 0.6
# Words carried by almost any Spanish headline, so counting them would make
# unrelated stories look alike.
_STOPWORDS = {
    "a", "al", "ante", "con", "de", "del", "el", "en", "era", "es", "la", "las", "los", "lo",
    "para", "por", "que", "se", "su", "sus", "un", "una", "y", "o", "tras", "sobre", "the",
}


def _headline_tokens(title: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", title.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", folded) if len(w) > 2 and w not in _STOPWORDS}


def _is_same_story(title: str, seen_tokens: list[set[str]]) -> bool:
    tokens = _headline_tokens(title)
    if not tokens:
        return False
    for other in seen_tokens:
        if not other:
            continue
        # Against the smaller headline, so a short title fully contained in a
        # longer one still counts as the same story.
        overlap = len(tokens & other) / min(len(tokens), len(other))
        if overlap >= _SAME_STORY_OVERLAP:
            return True
    return False


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

    # Skip stories already covered, and stories already picked up from
    # another feed in this same pass - the same headline reaches us through
    # all three feeds with a different Google News link each time, so the
    # URL check alone let a story be made twice.
    seen_tokens = [_headline_tokens(title) for title in recent_processed_titles()]

    candidates: list[dict] = []
    for index in range(max((len(items) for items in per_feed), default=0)):
        for items in per_feed:
            if index >= len(items):
                continue
            item = items[index]
            if _is_same_story(item["title"], seen_tokens):
                continue
            seen_tokens.append(_headline_tokens(item["title"]))
            candidates.append(item)
            if len(candidates) >= limit:
                return candidates
    return candidates
