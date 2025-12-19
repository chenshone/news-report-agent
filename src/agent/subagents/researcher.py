"""背景研究专家 SubAgent

负责补充背景信息，关联历史事件，需要使用搜索工具。
"""

from deepagents.middleware.subagents import SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import RESEARCHER_PROMPT
from ...tools import internet_search


def create_researcher(
    config: AppConfig,
    use_structured_output: bool = True,  # 暂不使用，保留接口一致性
) -> SubAgent:
    """
    创建背景研究专家 SubAgent
    
    注意：researcher 需要使用工具（internet_search），
    因此始终使用传统 SubAgent 模式。
    
    Args:
        config: 应用配置
        use_structured_output: 保留参数，暂不使用
        
    Returns:
        配置好的 SubAgent
    """
    model_config = config.model_for_role("researcher")
    model = create_chat_model(model_config, config)
    
    # researcher 需要工具，使用传统 SubAgent
    return SubAgent(
        name="researcher",
        description="补充背景信息，关联历史事件，返回结构化研究结果",
        system_prompt=RESEARCHER_PROMPT,
        tools=[internet_search],
        model=model,
    )


__all__ = ["create_researcher"]

