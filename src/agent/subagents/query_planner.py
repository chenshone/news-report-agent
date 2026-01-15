"""Query planner expert SubAgent for generating diverse search queries."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import QUERY_PLANNER_PROMPT, QUERY_PLANNER_PROMPT_STRUCTURED
from ...schemas import QueryPlannerOutput
from .base import create_structured_runnable


def create_query_planner(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """Create query planner expert SubAgent."""
    model_config = config.model_for_role("master")
    model = create_chat_model(model_config, config)

    if use_structured_output:
        return CompiledSubAgent(
            name="query_planner",
            description="分析用户需求，生成多维度搜索查询，返回结构化的查询计划（QueryPlannerOutput）",
            runnable=create_structured_runnable(
                model=model,
                output_schema=QueryPlannerOutput,
                system_prompt=QUERY_PLANNER_PROMPT_STRUCTURED,
            ),
        )

    return SubAgent(
        name="query_planner",
        description="分析用户需求，生成多维度搜索查询，并反思查询质量",
        system_prompt=QUERY_PLANNER_PROMPT,
        tools=[],
        model=model,
    )


__all__ = ["create_query_planner"]

