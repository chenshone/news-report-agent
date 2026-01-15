"""Fact checker expert SubAgent for verifying claims with search tools."""

from __future__ import annotations

from deepagents.middleware.subagents import SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import FACT_CHECKER_PROMPT
from ...tools import (
    fetch_page,
    internet_search,
    search_hackernews,
)


def create_fact_checker(
    config: AppConfig,
    use_structured_output: bool = True,
) -> SubAgent:
    """
    Create fact checker expert SubAgent.

    Note: Always uses SubAgent mode because it requires tool access.
    Equipped with multi-source verification tools:
    - internet_search: General web search
    - search_hackernews: Search HN discussions for community verification
    - fetch_page: Fetch original source for verification
    """
    model_config = config.model_for_role("fact_checker")
    model = create_chat_model(model_config, config)

    return SubAgent(
        name="fact_checker",
        description="核查关键事实声明的真实性，支持 HN 社区多源验证",
        system_prompt=FACT_CHECKER_PROMPT,
        tools=[
            internet_search,
            search_hackernews,
            fetch_page,
        ],
        model=model,
    )


__all__ = ["create_fact_checker"]

