"""SubAgent configuration module providing all expert SubAgent creators."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig
from .council import create_council
from .fact_checker import create_fact_checker
from .impact_assessor import create_impact_assessor
from .intent_analyzer import create_intent_analyzer
from .query_planner import create_query_planner
from .report_synthesizer import create_report_synthesizer
from .researcher import create_researcher
from .search_plan_generator import create_search_plan_generator
from .summarizer import create_summarizer
from .supervisor import create_supervisor


def get_subagent_configs(
    config: AppConfig,
    use_structured_output: bool = True,
    include_direct_experts: bool = True,
    include_query_understanding: bool = False,
) -> list[SubAgent | CompiledSubAgent]:
    """
    Get all expert SubAgent configurations.

    Args:
        config: Application configuration for model settings.
        use_structured_output: Whether to use Pydantic-based structured output.
        include_direct_experts: Whether to include individual expert SubAgents.
        include_query_understanding: Whether to include intent analyzer and search plan generator.

    Returns:
        List of configured SubAgents.
    """
    subagents: list[SubAgent | CompiledSubAgent] = [
        create_query_planner(config, use_structured_output),
    ]

    if include_query_understanding:
        subagents.extend([
            create_intent_analyzer(config),
            create_search_plan_generator(config),
        ])

    if include_direct_experts:
        subagents.extend([
            create_summarizer(config, use_structured_output),
            create_fact_checker(config, use_structured_output),
            create_researcher(config, use_structured_output),
            create_impact_assessor(config, use_structured_output),
            create_supervisor(config, use_structured_output),
            create_report_synthesizer(config, use_structured_output),
        ])

    subagents.append(create_council(config))
    return subagents


__all__ = [
    "get_subagent_configs",
    "create_council",
    "create_fact_checker",
    "create_impact_assessor",
    "create_intent_analyzer",
    "create_query_planner",
    "create_report_synthesizer",
    "create_researcher",
    "create_search_plan_generator",
    "create_summarizer",
    "create_supervisor",
]

