"""Agent module for news report agent.

提供 Agent 创建和配置功能：
- master: MasterAgent 创建
- subagents: 专家 SubAgent 配置
- council: 专家委员会协作机制
"""

from .master import create_news_agent
from .subagents import get_subagent_configs
from .council import (
    CROSS_REVIEW_MATRIX,
    EXPERT_DESCRIPTIONS,
    CrossReviewResult,
    DiscussionPoint,
    ExpertOutput,
    Grade,
    ReviewType,
    generate_chairman_synthesis_prompt,
    generate_cross_review_prompt,
    generate_discussion_prompt,
)

__all__ = [
    # Master agent
    "create_news_agent",
    # SubAgent config
    "get_subagent_configs",
    # Expert council
    "CROSS_REVIEW_MATRIX",
    "EXPERT_DESCRIPTIONS",
    "CrossReviewResult",
    "DiscussionPoint",
    "ExpertOutput",
    "Grade",
    "ReviewType",
    "generate_chairman_synthesis_prompt",
    "generate_cross_review_prompt",
    "generate_discussion_prompt",
]
