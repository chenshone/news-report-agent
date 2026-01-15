"""Summarizer expert SubAgent for extracting news highlights."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import SUMMARIZER_PROMPT, SUMMARIZER_PROMPT_STRUCTURED
from ...schemas import SummaryOutput
from .base import create_structured_runnable


def create_summarizer(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """Create summarizer expert SubAgent."""
    model_config = config.model_for_role("summarizer")
    model = create_chat_model(model_config, config)

    if use_structured_output:
        return CompiledSubAgent(
            name="summarizer",
            description="提取新闻核心要点，返回结构化摘要（SummaryOutput）",
            runnable=create_structured_runnable(
                model=model,
                output_schema=SummaryOutput,
                system_prompt=SUMMARIZER_PROMPT_STRUCTURED,
            ),
        )

    return SubAgent(
        name="summarizer",
        description="提取新闻核心要点，生成结构化摘要",
        system_prompt=SUMMARIZER_PROMPT,
        tools=[],
        model=model,
    )


__all__ = ["create_summarizer"]

