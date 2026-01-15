"""Expert supervisor SubAgent acting as LLM Council Chairman."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import EXPERT_SUPERVISOR_PROMPT, EXPERT_SUPERVISOR_PROMPT_STRUCTURED
from ...schemas import SupervisorOutput
from .base import create_structured_runnable


def create_supervisor(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """Create expert supervisor SubAgent."""
    model_config = config.model_for_role("master")
    model = create_chat_model(model_config, config)

    if use_structured_output:
        return CompiledSubAgent(
            name="expert_supervisor",
            description="审核各专家分析结果，协调讨论，返回结构化整合结果（SupervisorOutput）",
            runnable=create_structured_runnable(
                model=model,
                output_schema=SupervisorOutput,
                system_prompt=EXPERT_SUPERVISOR_PROMPT_STRUCTURED,
            ),
        )

    return SubAgent(
        name="expert_supervisor",
        description="审核各专家分析结果，协调讨论，确认最终整合内容",
        system_prompt=EXPERT_SUPERVISOR_PROMPT,
        tools=[],
        model=model,
    )


__all__ = ["create_supervisor"]

