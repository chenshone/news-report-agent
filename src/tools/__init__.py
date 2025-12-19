"""Custom tools for the news report agent.

提供 MasterAgent 使用的工具：
- search: 网络搜索
- scraper: 网页抓取
- evaluator: 内容评估（可信度、相关性）
"""

from .evaluator import evaluate_credibility, evaluate_relevance
from .scraper import fetch_page
from .search import internet_search

__all__ = [
    # 搜索与抓取
    "internet_search",
    "fetch_page",
    # 评估
    "evaluate_credibility",
    "evaluate_relevance",
]
