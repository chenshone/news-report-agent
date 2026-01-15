"""GitHub search tools for trending repos and code search.

Uses GitHub's public API for searching repositories.
No API key required for basic usage, but rate-limited.
"""

from __future__ import annotations

import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from .base import build_error_result


def _make_github_request(url: str) -> dict[str, Any] | None:
    """Make a request to GitHub API with proper headers."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "News-Report-Agent/1.0",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _format_repo_result(repo: dict[str, Any], source_name: str = "GitHub") -> dict[str, Any]:
    """Format a GitHub repo to our standard format."""
    # Format date
    updated_at = repo.get("updated_at", "")
    if updated_at:
        try:
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            updated_at = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

    return {
        "title": repo.get("full_name", repo.get("name", "Unknown")),
        "url": repo.get("html_url", ""),
        "content": repo.get("description", "") or "No description available",
        "source_type": "github",
        "source_name": source_name,
        "published_date": updated_at,
        "score": repo.get("stargazers_count", 0) / 1000,  # Normalize stars to a score
        "metadata": {
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language", ""),
            "topics": repo.get("topics", []),
            "open_issues": repo.get("open_issues_count", 0),
            "license": repo.get("license", {}).get("spdx_id", "") if repo.get("license") else "",
        },
    }


@tool
def search_github_repos(
    query: str,
    max_results: int = 10,
    sort: str = "updated",
    language: str | None = None,
    min_stars: int = 0,
) -> list[dict[str, Any]]:
    """
    Search GitHub repositories by keyword.

    Use this tool to find open-source projects, libraries, and frameworks.
    Best for: Finding specific projects, comparing alternatives, tracking updates.

    Args:
        query: Search query (e.g., "AI agent framework", "LLM tools").
        max_results: Maximum number of repos to return (default: 10, max: 30).
        sort: Sort by "stars", "updated", or "forks" (default: "updated").
        language: Filter by programming language (e.g., "python", "javascript").
        min_stars: Minimum number of stars (default: 0).

    Returns:
        List of repositories with name, description, stars, language, and topics.
    """
    max_results = min(max(1, max_results), 30)

    try:
        # Build search query
        search_parts = [query]
        if language:
            search_parts.append(f"language:{language}")
        if min_stars > 0:
            search_parts.append(f"stars:>={min_stars}")

        search_query = " ".join(search_parts)
        encoded_query = urllib.parse.quote(search_query)

        # Map sort parameter
        sort_param = sort if sort in ["stars", "updated", "forks"] else "updated"
        order = "desc"

        url = f"https://api.github.com/search/repositories?q={encoded_query}&sort={sort_param}&order={order}&per_page={max_results}"

        response = _make_github_request(url)
        if not response:
            return build_error_result(
                "github",
                "GitHub API request failed",
                "Failed to fetch data from GitHub. This might be due to rate limiting.",
            )

        items = response.get("items", [])
        if not items:
            return [
                {
                    "title": f"No repositories found for: {query}",
                    "url": "",
                    "content": f"No GitHub repositories matching '{query}' were found. "
                    "Try different keywords or remove filters.",
                    "source_type": "github",
                    "source_name": "GitHub",
                    "score": 0.0,
                }
            ]

        return [_format_repo_result(repo, "GitHub Search") for repo in items]

    except Exception as e:
        return build_error_result("github", f"GitHub search error: {type(e).__name__}", str(e))


@tool
def search_github_trending(
    language: str | None = None,
    since: str = "weekly",
    spoken_language: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get trending GitHub repositories.

    Use this tool to discover popular and emerging open-source projects.
    Best for: Finding new projects, tracking what's gaining traction, tech trends.

    Args:
        language: Filter by programming language (e.g., "python", "rust").
        since: Time range - "daily", "weekly", or "monthly" (default: "weekly").
        spoken_language: Filter by spoken language (e.g., "en", "zh").

    Returns:
        List of trending repos with name, description, stars, and weekly growth.

    Note:
        Uses GitHub Search API with date filters as trending API is unofficial.
        Results approximate trending by recent activity and star count.
    """
    try:
        # Calculate date range
        days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Build search query for recently active repos with good star count
        search_parts = [f"created:>={since_date}", "stars:>=50"]
        if language:
            search_parts.append(f"language:{language}")

        search_query = " ".join(search_parts)
        encoded_query = urllib.parse.quote(search_query)

        url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page=20"

        response = _make_github_request(url)
        if not response:
            return build_error_result(
                "github",
                "GitHub API request failed",
                "Failed to fetch trending data from GitHub. This might be due to rate limiting.",
            )

        items = response.get("items", [])
        if not items:
            lang_info = f" for {language}" if language else ""
            return [
                {
                    "title": f"No trending repos found{lang_info}",
                    "url": "",
                    "content": f"No trending repositories found in the {since} timeframe. "
                    "Try a different time range or language.",
                    "source_type": "github",
                    "source_name": "GitHub Trending",
                    "score": 0.0,
                }
            ]

        results = []
        for repo in items:
            result = _format_repo_result(repo, "GitHub Trending")
            # Add trending-specific metadata
            result["metadata"]["since"] = since
            result["metadata"]["period_days"] = days
            results.append(result)

        return results

    except Exception as e:
        return build_error_result("github", f"GitHub trending error: {type(e).__name__}", str(e))


__all__ = ["search_github_repos", "search_github_trending"]
