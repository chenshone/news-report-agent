"""RSS feed aggregation tool for news and blog content.

Uses feedparser to aggregate RSS feeds from various tech sources.
No API key required - fully free.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import tool

from .base import build_error_result


# Pre-defined high-quality RSS feeds organized by category
DEFAULT_FEEDS: dict[str, list[dict[str, str]]] = {
    "tech": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
        {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    ],
    "ai": [
        {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss/"},
        {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default?alt=rss"},
        {"name": "Anthropic Blog", "url": "https://www.anthropic.com/rss.xml"},
        {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    ],
    "dev": [
        {"name": "Dev.to", "url": "https://dev.to/feed"},
        {"name": "Hacker Noon", "url": "https://hackernoon.com/feed"},
        {"name": "CSS-Tricks", "url": "https://css-tricks.com/feed/"},
    ],
    "cn": [
        {"name": "36氪", "url": "https://36kr.com/feed"},
        {"name": "少数派", "url": "https://sspai.com/feed"},
        {"name": "InfoQ 中文", "url": "https://www.infoq.cn/feed"},
    ],
    "newsletters": [
        {"name": "The Batch (DeepLearning.AI)", "url": "https://www.deeplearning.ai/the-batch/feed/"},
        {"name": "Import AI", "url": "https://importai.substack.com/feed"},
        {"name": "TLDR Newsletter", "url": "https://tldr.tech/api/rss/tech"},
    ],
}


def _parse_date(entry: Any) -> datetime | None:
    """Parse date from RSS entry."""
    for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
        date_tuple = getattr(entry, date_field, None)
        if date_tuple:
            try:
                return datetime(*date_tuple[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _format_rss_result(entry: Any, feed_name: str, feed_url: str) -> dict[str, Any]:
    """Format an RSS entry to our standard format."""
    # Get published date
    pub_date = _parse_date(entry)
    pub_date_str = pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else ""

    # Get content - prefer summary, fall back to content
    content = ""
    if hasattr(entry, "summary"):
        content = entry.summary
    elif hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")

    # Strip HTML tags for cleaner content (simple approach)
    import re

    content = re.sub(r"<[^>]+>", "", content)
    content = content[:500] + "..." if len(content) > 500 else content

    return {
        "title": getattr(entry, "title", "Untitled"),
        "url": getattr(entry, "link", ""),
        "content": content or "No content available",
        "source_type": "rss",
        "source_name": feed_name,
        "published_date": pub_date_str,
        "score": 0.5,  # RSS doesn't have relevance scores
        "metadata": {
            "feed_url": feed_url,
            "author": getattr(entry, "author", ""),
            "tags": [tag.get("term", "") for tag in getattr(entry, "tags", [])][:5],
        },
    }


@tool
def fetch_rss_feeds(
    categories: list[str] | None = None,
    custom_feeds: list[str] | None = None,
    max_per_feed: int = 5,
    hours_back: int = 48,
) -> list[dict[str, Any]]:
    """
    Aggregate content from RSS feeds of tech news sites and blogs.

    Use this tool to get latest articles from specific publications.
    Best for: News coverage, blog posts, official announcements.

    Args:
        categories: List of feed categories to fetch from:
            - "tech": TechCrunch, The Verge, Ars Technica, Wired
            - "ai": OpenAI, Google AI, Anthropic, Hugging Face blogs
            - "dev": Dev.to, Hacker Noon, CSS-Tricks
            - "cn": 36氪, 少数派, InfoQ 中文
            - "newsletters": The Batch, Import AI, TLDR
            If None, defaults to ["tech", "ai"].
        custom_feeds: Optional list of custom RSS feed URLs to include.
        max_per_feed: Maximum articles per feed (default: 5).
        hours_back: Only include articles from last N hours (default: 48).

    Returns:
        List of articles with title, content, source, and publication date.
    """
    try:
        import feedparser
    except ImportError:
        return build_error_result(
            "rss",
            "Error: feedparser not installed",
            "Please install feedparser: pip install feedparser",
        )

    # Default categories if not specified
    if not categories:
        categories = ["tech", "ai"]

    max_per_feed = min(max(1, max_per_feed), 20)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    # Collect feeds to fetch
    feeds_to_fetch: list[dict[str, str]] = []
    for cat in categories:
        if cat in DEFAULT_FEEDS:
            feeds_to_fetch.extend(DEFAULT_FEEDS[cat])

    # Add custom feeds
    if custom_feeds:
        for url in custom_feeds:
            feeds_to_fetch.append({"name": "Custom Feed", "url": url})

    if not feeds_to_fetch:
        return build_error_result(
            "rss",
            "No feeds to fetch",
            f"No valid categories specified. Available: {list(DEFAULT_FEEDS.keys())}",
        )

    results = []
    errors = []

    for feed_info in feeds_to_fetch:
        feed_name = feed_info["name"]
        feed_url = feed_info["url"]

        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                errors.append(f"{feed_name}: Parse error")
                continue

            count = 0
            for entry in feed.entries:
                if count >= max_per_feed:
                    break

                # Check date filter
                pub_date = _parse_date(entry)
                if pub_date and pub_date < cutoff_time:
                    continue

                results.append(_format_rss_result(entry, feed_name, feed_url))
                count += 1

        except Exception as e:
            errors.append(f"{feed_name}: {type(e).__name__}")
            continue

    if not results:
        error_info = f" Errors: {', '.join(errors)}" if errors else ""
        return [
            {
                "title": "No recent articles found",
                "url": "",
                "content": f"No articles found in the last {hours_back} hours from the selected feeds.{error_info}",
                "source_type": "rss",
                "source_name": "RSS Aggregator",
                "score": 0.0,
            }
        ]

    # Sort by date (newest first)
    results.sort(key=lambda x: x.get("published_date", ""), reverse=True)

    return results


__all__ = ["fetch_rss_feeds"]
