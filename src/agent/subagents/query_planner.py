"""查询规划专家 SubAgent

负责分析用户需求，生成多维度、多样化的搜索查询。
"""

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig, create_chat_model
from ...prompts import QUERY_PLANNER_PROMPT, QUERY_PLANNER_PROMPT_STRUCTURED
from ...schemas import QueryPlannerOutput
from .base import create_structured_runnable


def create_query_planner(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent | SubAgent:
    """
    创建查询规划专家 SubAgent
    
    Args:
        config: 应用配置
        use_structured_output: 是否使用结构化输出
        
    Returns:
        配置好的 SubAgent
    """
    model_config = config.model_for_role("master")  # 查询规划需要强推理
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
    else:
        return SubAgent(
            name="query_planner",
            description="分析用户需求，生成多维度搜索查询，并反思查询质量",
            system_prompt=QUERY_PLANNER_PROMPT,
            tools=[],
            model=model,
        )


__all__ = ["create_query_planner"]

