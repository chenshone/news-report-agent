"""影响评估专家 SubAgent

负责评估短期/长期影响，预测发展趋势。
"""

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import IMPACT_ASSESSOR_PROMPT, IMPACT_ASSESSOR_PROMPT_STRUCTURED
from ...schemas import ImpactAssessorOutput
from .base import create_structured_runnable


def create_impact_assessor(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """
    创建影响评估专家 SubAgent
    
    Args:
        config: 应用配置
        use_structured_output: 是否使用结构化输出
        
    Returns:
        配置好的 SubAgent
    """
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
    else:
        return SubAgent(
            name="impact_assessor",
            description="评估短期/长期影响，预测发展趋势",
            system_prompt=IMPACT_ASSESSOR_PROMPT,
            tools=[],
            model=model,
        )


__all__ = ["create_impact_assessor"]

