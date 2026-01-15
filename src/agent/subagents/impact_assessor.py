"""Impact assessor expert SubAgent for evaluating news implications."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import IMPACT_ASSESSOR_PROMPT, IMPACT_ASSESSOR_PROMPT_STRUCTURED
from ...schemas import ImpactAssessorOutput
from .base import create_structured_runnable


def create_impact_assessor(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """Create impact assessor expert SubAgent."""
    model_config = config.model_for_role("impact_assessor")
    model = create_chat_model(model_config, config)

    if use_structured_output:
        return CompiledSubAgent(
            name="impact_assessor",
            description="评估短期/长期影响，预测发展趋势，返回结构化评估结果（ImpactAssessorOutput）",
            runnable=create_structured_runnable(
                model=model,
                output_schema=ImpactAssessorOutput,
                system_prompt=IMPACT_ASSESSOR_PROMPT_STRUCTURED,
            ),
        )

    return SubAgent(
        name="impact_assessor",
        description="评估短期/长期影响，预测发展趋势",
        system_prompt=IMPACT_ASSESSOR_PROMPT,
        tools=[],
        model=model,
    )


__all__ = ["create_impact_assessor"]

