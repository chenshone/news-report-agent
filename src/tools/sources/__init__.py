"""Multi-source intelligence layer for diverse information retrieval.

Provides tools to search multiple information sources:
- arXiv: Academic papers and research
- GitHub: Trending repos and code search
- Hacker News: Tech community discussions
- RSS: News feed aggregation
"""

from __future__ import annotations

from .arxiv import search_arxiv
from .github import search_github_repos, search_github_trending
from .hackernews import get_hackernews_top, search_hackernews
from .rss import fetch_rss_feeds

__all__ = [
    "search_arxiv",
    "search_github_repos",
    "search_github_trending",
    "search_hackernews",
    "get_hackernews_top",
    "fetch_rss_feeds",
]
