"""SubAgent 配置模块

提供所有专家 SubAgent 的创建函数和统一配置接口。

每个专家一个独立文件：
- query_planner: 查询规划专家
- summarizer: 摘要专家
- fact_checker: 事实核查专家
- researcher: 背景研究专家
- impact_assessor: 影响评估专家
- supervisor: 专家主管
- council: 专家委员会（封装四阶段流程）
"""

from typing import Union

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent

from ...config import AppConfig
from .query_planner import create_query_planner
from .summarizer import create_summarizer
from .fact_checker import create_fact_checker
from .researcher import create_researcher
from .impact_assessor import create_impact_assessor
from .supervisor import create_supervisor
from .council import create_council


def get_subagent_configs(
    config: AppConfig,
    use_structured_output: bool = True,
) -> list[Union[SubAgent, CompiledSubAgent]]:
    """
    获取所有专家子Agent配置。
    
    Args:
        config: 应用配置，用于获取模型设置
        use_structured_output: 是否使用结构化输出模式（推荐 True）
        
    Returns:
        子Agent配置列表
    """
    return [
        create_query_planner(config, use_structured_output),
        create_summarizer(config, use_structured_output),
        create_fact_checker(config, use_structured_output),
        create_researcher(config, use_structured_output),
        create_impact_assessor(config, use_structured_output),
        create_supervisor(config, use_structured_output),
        create_council(config),
    ]


__all__ = [
    # Main config function
    "get_subagent_configs",
    # Individual creators
    "create_query_planner",
    "create_summarizer",
    "create_fact_checker",
    "create_researcher",
    "create_impact_assessor",
    "create_supervisor",
    "create_council",
]

