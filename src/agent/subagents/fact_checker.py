"""事实核查专家 SubAgent

负责核查关键事实声明的真实性，需要使用搜索工具验证。
"""

from deepagents.middleware.subagents import SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import FACT_CHECKER_PROMPT
from ...tools import internet_search


def create_fact_checker(
    config: AppConfig,
    use_structured_output: bool = True,  # 暂不使用，保留接口一致性
) -> SubAgent:
    """
    创建事实核查专家 SubAgent
    
    注意：fact_checker 需要使用工具（internet_search），
    因此始终使用传统 SubAgent 模式。
    
    Args:
        config: 应用配置
        use_structured_output: 保留参数，暂不使用
        
    Returns:
        配置好的 SubAgent
    """
    model_config = config.model_for_role("fact_checker")
    model = create_chat_model(model_config, config)
    
    # fact_checker 需要工具，使用传统 SubAgent
    return SubAgent(
        name="fact_checker",
        description="核查关键事实声明的真实性，返回结构化核查结果",
        system_prompt=FACT_CHECKER_PROMPT,
        tools=[internet_search],
        model=model,
    )


__all__ = ["create_fact_checker"]

