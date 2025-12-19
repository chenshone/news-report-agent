"""摘要专家 SubAgent

负责提取新闻核心要点，生成结构化摘要。
"""

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import SUMMARIZER_PROMPT, SUMMARIZER_PROMPT_STRUCTURED
from ...schemas import SummaryOutput
from .base import create_structured_runnable


def create_summarizer(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """
    创建摘要专家 SubAgent
    
    Args:
        config: 应用配置
        use_structured_output: 是否使用结构化输出
        
    Returns:
        配置好的 SubAgent
    """
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
    else:
        return SubAgent(
            name="summarizer",
            description="提取新闻核心要点，生成结构化摘要",
            system_prompt=SUMMARIZER_PROMPT,
            tools=[],
            model=model,
        )


__all__ = ["create_summarizer"]

