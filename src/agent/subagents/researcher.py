"""Researcher expert SubAgent for providing background context."""

from __future__ import annotations

from deepagents.middleware.subagents import SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import RESEARCHER_PROMPT
from ...tools import (
    fetch_page,
    internet_search,
    search_arxiv,
    search_github_repos,
)


def create_researcher(
    config: AppConfig,
    use_structured_output: bool = True,
) -> SubAgent:
    """
    Create researcher expert SubAgent.

    Note: Always uses SubAgent mode because it requires tool access.
    Equipped with multi-source research tools:
    - internet_search: General web search
    - search_arxiv: Academic paper search
    - search_github_repos: GitHub repository search
    - fetch_page: Fetch page details
    """
    model_config = config.model_for_role("researcher")
    model = create_chat_model(model_config, config)

    return SubAgent(
        name="researcher",
        description="补充背景信息，关联历史事件，支持 arXiv/GitHub 多源研究",
        system_prompt=RESEARCHER_PROMPT,
        tools=[
            internet_search,
            search_arxiv,
            search_github_repos,
            fetch_page,
        ],
        model=model,
    )


__all__ = ["create_researcher"]

