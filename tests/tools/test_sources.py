"""Tests for multi-source intelligence tools."""

from __future__ import annotations

import pytest

# Mark all tests as slow/integration since they make real API calls
pytestmark = pytest.mark.slow


class TestArxivSearch:
    """Tests for arXiv search tool."""

    def test_search_arxiv_basic(self):
        """Test basic arXiv search."""
        from src.tools.sources.arxiv import search_arxiv

        results = search_arxiv.invoke({
            "query": "large language models",
            "max_results": 3,
            "days_back": 30,
        })

        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check result structure
        result = results[0]
        assert "title" in result
        assert "url" in result
        assert "content" in result
        assert result["source_type"] == "arxiv"

    def test_search_arxiv_with_categories(self):
        """Test arXiv search with category filter."""
        from src.tools.sources.arxiv import search_arxiv

        results = search_arxiv.invoke({
            "query": "transformer",
            "max_results": 3,
            "categories": ["cs.AI", "cs.LG"],
            "days_back": 30,
        })

        assert isinstance(results, list)


class TestGitHubSearch:
    """Tests for GitHub search tools."""

    def test_search_github_repos_basic(self):
        """Test basic GitHub repo search."""
        from src.tools.sources.github import search_github_repos

        results = search_github_repos.invoke({
            "query": "AI agent",
            "max_results": 5,
        })

        assert isinstance(results, list)
        assert len(results) > 0
        
        result = results[0]
        assert "title" in result
        assert "url" in result
        assert result["source_type"] == "github"
        assert "stars" in result.get("metadata", {})

    def test_search_github_repos_with_language(self):
        """Test GitHub repo search with language filter."""
        from src.tools.sources.github import search_github_repos

        results = search_github_repos.invoke({
            "query": "machine learning",
            "max_results": 3,
            "language": "python",
        })

        assert isinstance(results, list)

    def test_search_github_trending(self):
        """Test GitHub trending repos."""
        from src.tools.sources.github import search_github_trending

        results = search_github_trending.invoke({
            "since": "weekly",
        })

        assert isinstance(results, list)
        assert len(results) > 0


class TestHackerNewsSearch:
    """Tests for Hacker News search tools."""

    def test_search_hackernews_basic(self):
        """Test basic Hacker News search."""
        from src.tools.sources.hackernews import search_hackernews

        results = search_hackernews.invoke({
            "query": "AI",
            "max_results": 5,
        })

        assert isinstance(results, list)
        assert len(results) > 0
        
        result = results[0]
        assert "title" in result
        assert "url" in result
        assert result["source_type"] == "hackernews"

    def test_search_hackernews_with_time_range(self):
        """Test Hacker News search with time filter."""
        from src.tools.sources.hackernews import search_hackernews

        results = search_hackernews.invoke({
            "query": "machine learning",
            "max_results": 5,
            "time_range": "week",
        })

        assert isinstance(results, list)

    def test_get_hackernews_top(self):
        """Test getting HN top stories."""
        from src.tools.sources.hackernews import get_hackernews_top

        results = get_hackernews_top.invoke({
            "category": "topstories",
            "max_results": 10,
        })

        assert isinstance(results, list)
        assert len(results) > 0
        
        result = results[0]
        assert "title" in result
        assert "points" in result.get("metadata", {})


class TestRSSFeeds:
    """Tests for RSS feed aggregation."""

    def test_fetch_rss_feeds_basic(self):
        """Test basic RSS feed fetching."""
        from src.tools.sources.rss import fetch_rss_feeds

        results = fetch_rss_feeds.invoke({
            "categories": ["ai"],
            "max_per_feed": 2,
            "hours_back": 168,  # 1 week
        })

        assert isinstance(results, list)
        
        # Check that we got some results (might be empty if no recent posts)
        if len(results) > 0:
            result = results[0]
            assert "title" in result
            assert result["source_type"] == "rss"

    def test_fetch_rss_feeds_multiple_categories(self):
        """Test RSS fetching from multiple categories."""
        from src.tools.sources.rss import fetch_rss_feeds

        results = fetch_rss_feeds.invoke({
            "categories": ["tech", "ai"],
            "max_per_feed": 2,
            "hours_back": 168,
        })

        assert isinstance(results, list)


class TestToolsIntegration:
    """Integration tests for tools with MasterAgent."""

    def test_tools_import(self):
        """Test that all tools can be imported."""
        from src.tools import (
            search_arxiv,
            search_github_repos,
            search_github_trending,
            search_hackernews,
            get_hackernews_top,
            fetch_rss_feeds,
        )

        # Verify they are LangChain tools
        assert hasattr(search_arxiv, "invoke")
        assert hasattr(search_github_repos, "invoke")
        assert hasattr(search_github_trending, "invoke")
        assert hasattr(search_hackernews, "invoke")
        assert hasattr(get_hackernews_top, "invoke")
        assert hasattr(fetch_rss_feeds, "invoke")
