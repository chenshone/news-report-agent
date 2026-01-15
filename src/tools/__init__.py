"""Custom tools for the news report agent.

提供 MasterAgent 使用的工具：
- search: 网络搜索
- scraper: 网页抓取
- evaluator: 内容评估（可信度、相关性）
- sources: 多源信息获取（arXiv、GitHub、Hacker News、RSS）
"""

from .evaluator import evaluate_credibility, evaluate_relevance
from .scraper import fetch_page
from .search import internet_search

# Multi-source intelligence tools
from .sources import (
    fetch_rss_feeds,
    get_hackernews_top,
    search_arxiv,
    search_github_repos,
    search_github_trending,
    search_hackernews,
)

__all__ = [
    # 搜索与抓取
    "internet_search",
    "fetch_page",
    # 评估
    "evaluate_credibility",
    "evaluate_relevance",
    # 多源信息获取
    "search_arxiv",
    "search_github_repos",
    "search_github_trending",
    "search_hackernews",
    "get_hackernews_top",
    "fetch_rss_feeds",
]
