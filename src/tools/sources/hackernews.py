"""Hacker News search tools for tech community discussions.

Uses the Algolia HN Search API (free, no auth required) and official HN API.
"""

from __future__ import annotations

import urllib.request
import urllib.parse
import json
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from .base import build_error_result


def _make_hn_request(url: str) -> dict[str, Any] | list[Any] | None:
    """Make a request to HN API."""
    headers = {"User-Agent": "News-Report-Agent/1.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _format_hn_result(hit: dict[str, Any]) -> dict[str, Any]:
    """Format an Algolia HN search result to our standard format."""
    # Format date
    created_at = hit.get("created_at", "")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            created_at = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            pass

    story_id = hit.get("objectID", hit.get("story_id", ""))
    hn_url = f"https://news.ycombinator.com/item?id={story_id}" if story_id else ""

    # Get external URL or HN discussion URL
    url = hit.get("url") or hn_url

    return {
        "title": hit.get("title", hit.get("story_title", "Untitled")),
        "url": url,
        "content": hit.get("story_text", "") or hit.get("comment_text", "") or "No content available",
        "source_type": "hackernews",
        "source_name": "Hacker News",
        "published_date": created_at,
        "score": hit.get("points", 0) / 100 if hit.get("points") else 0.0,
        "metadata": {
            "hn_id": story_id,
            "hn_url": hn_url,
            "points": hit.get("points", 0),
            "num_comments": hit.get("num_comments", 0),
            "author": hit.get("author", ""),
            "type": hit.get("_tags", ["unknown"])[0] if hit.get("_tags") else "story",
        },
    }


@tool
def search_hackernews(
    query: str,
    max_results: int = 15,
    search_type: str = "story",
    sort_by: str = "relevance",
    time_range: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search Hacker News discussions and articles.

    Use this tool to understand tech community opinions, discussions, and sentiment.
    Best for: Community reactions, technical debates, startup/product feedback.

    Args:
        query: Search query (e.g., "GPT-4", "startup layoffs", "Rust vs Go").
        max_results: Maximum results to return (default: 15, max: 50).
        search_type: Type to search - "story", "comment", or "all" (default: "story").
        sort_by: Sort by "relevance" or "date" (default: "relevance").
        time_range: Optional time filter - "24h", "week", "month", "year".

    Returns:
        List of HN posts with title, points, comments count, and discussion link.
    """
    max_results = min(max(1, max_results), 50)

    try:
        # Build Algolia HN Search URL
        base_url = "https://hn.algolia.com/api/v1"
        endpoint = "search" if sort_by == "relevance" else "search_by_date"

        # Build query params
        params = {
            "query": query,
            "hitsPerPage": max_results,
        }

        # Add type filter
        if search_type == "story":
            params["tags"] = "story"
        elif search_type == "comment":
            params["tags"] = "comment"

        # Add time filter
        if time_range:
            time_map = {
                "24h": 86400,
                "week": 604800,
                "month": 2592000,
                "year": 31536000,
            }
            seconds = time_map.get(time_range.lower())
            if seconds:
                params["numericFilters"] = f"created_at_i>{int(datetime.now().timestamp()) - seconds}"

        query_string = urllib.parse.urlencode(params)
        url = f"{base_url}/{endpoint}?{query_string}"

        response = _make_hn_request(url)
        if not response or not isinstance(response, dict):
            return build_error_result(
                "hackernews",
                "Hacker News API request failed",
                "Failed to fetch data from Hacker News search.",
            )

        hits = response.get("hits", [])
        if not hits:
            return [
                {
                    "title": f"No HN discussions found for: {query}",
                    "url": "",
                    "content": f"No Hacker News posts matching '{query}' were found. "
                    "Try different keywords or remove time filters.",
                    "source_type": "hackernews",
                    "source_name": "Hacker News",
                    "score": 0.0,
                }
            ]

        return [_format_hn_result(hit) for hit in hits]

    except Exception as e:
        return build_error_result("hackernews", f"HN search error: {type(e).__name__}", str(e))


def _get_item_details(item_id: int) -> dict[str, Any] | None:
    """Get details for a single HN item."""
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    return _make_hn_request(url)


@tool
def get_hackernews_top(
    category: str = "topstories",
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """
    Get top/new/best stories from Hacker News.

    Use this tool to see what's currently popular in the tech community.
    Best for: Current hot topics, breaking tech news, trending discussions.

    Args:
        category: Category to fetch:
            - "topstories": Current top stories (default)
            - "newstories": Latest submissions
            - "beststories": Highest voted stories
            - "askstories": Ask HN posts
            - "showstories": Show HN posts
        max_results: Maximum stories to return (default: 20, max: 30).

    Returns:
        List of top HN stories with title, points, comments, and links.
    """
    max_results = min(max(1, max_results), 30)

    valid_categories = ["topstories", "newstories", "beststories", "askstories", "showstories"]
    if category not in valid_categories:
        category = "topstories"

    try:
        # Get story IDs
        ids_url = f"https://hacker-news.firebaseio.com/v0/{category}.json"
        story_ids = _make_hn_request(ids_url)

        if not story_ids or not isinstance(story_ids, list):
            return build_error_result(
                "hackernews",
                "Failed to fetch HN stories",
                "Could not retrieve story IDs from Hacker News.",
            )

        # Fetch details for top N stories
        results = []
        for story_id in story_ids[:max_results]:
            item = _get_item_details(story_id)
            if item and item.get("type") == "story":
                # Format the item
                created_at = ""
                if item.get("time"):
                    created_at = datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M")

                hn_url = f"https://news.ycombinator.com/item?id={story_id}"
                url = item.get("url") or hn_url

                results.append(
                    {
                        "title": item.get("title", "Untitled"),
                        "url": url,
                        "content": f"Points: {item.get('score', 0)} | Comments: {item.get('descendants', 0)} | "
                        f"By: {item.get('by', 'unknown')}",
                        "source_type": "hackernews",
                        "source_name": f"Hacker News - {category.replace('stories', '').title()}",
                        "published_date": created_at,
                        "score": item.get("score", 0) / 100,
                        "metadata": {
                            "hn_id": story_id,
                            "hn_url": hn_url,
                            "points": item.get("score", 0),
                            "num_comments": item.get("descendants", 0),
                            "author": item.get("by", ""),
                            "type": item.get("type", "story"),
                            "category": category,
                        },
                    }
                )

        if not results:
            return [
                {
                    "title": f"No stories found in {category}",
                    "url": "",
                    "content": "Could not fetch any stories from this category.",
                    "source_type": "hackernews",
                    "source_name": "Hacker News",
                    "score": 0.0,
                }
            ]

        return results

    except Exception as e:
        return build_error_result("hackernews", f"HN top stories error: {type(e).__name__}", str(e))


__all__ = ["search_hackernews", "get_hackernews_top"]
