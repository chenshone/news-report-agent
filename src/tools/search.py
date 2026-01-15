"""Internet search tool using Tavily API."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from langchain_core.tools import tool


def _build_error_result(title: str, content: str) -> list[dict[str, Any]]:
    """Build a standardized error result."""
    return [{"title": title, "url": "", "content": content, "source": "error", "score": 0.0}]


def _transform_tavily_results(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform Tavily response to our standard format."""
    results = []
    for item in response.get("results", []):
        url = item.get("url", "")
        result: dict[str, Any] = {
            "title": item.get("title", ""),
            "url": url,
            "content": item.get("content", ""),
            "source": url.split("/")[2] if url else "",
            "score": item.get("score", 0.0),
        }
        if "published_date" in item:
            result["published_date"] = item["published_date"]
        results.append(result)
    return results


@tool
def internet_search(
    query: str,
    max_results: int = 8,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search the internet for relevant news and information.

    Uses the Tavily API to search for high-quality, recent content.

    Args:
        query: The search query string.
        max_results: Maximum number of results (default: 8, max: 10).
        topic: Optional topic hint (e.g., "news", "general").

    Returns:
        A list of search results with title, url, content, source, score,
        and optionally published_date.
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        return _build_error_result(
            "Error: Tavily not installed",
            "Please install tavily-python: pip install tavily-python",
        )

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return _build_error_result(
            "Error: TAVILY_API_KEY not set",
            "Please set TAVILY_API_KEY environment variable",
        )

    max_results = min(max(1, max_results), 10)

    try:
        client = TavilyClient(api_key=api_key)
        search_params: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_raw_content": False,
        }
        if topic:
            search_params["topic"] = topic

        response = client.search(**search_params)
        return _transform_tavily_results(response)

    except Exception as e:
        return _build_error_result(f"Search error: {type(e).__name__}", str(e))


@tool
async def internet_search_async(
    query: str,
    max_results: int = 5,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    """Async version of internet_search for async agent workflows."""
    return await asyncio.to_thread(
        internet_search.invoke,
        {"query": query, "max_results": max_results, "topic": topic},
    )


__all__ = ["internet_search", "internet_search_async"]
