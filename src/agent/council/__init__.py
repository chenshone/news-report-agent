"""专家委员会协作模块

包含 LLM Council 风格的交叉评审和共识讨论机制：
- matrix: 交叉评审矩阵和 Prompt 模板
- coordinator: 高级讨论协调器（可选使用）
"""

from .matrix import (
    # Enums and data classes
    Grade,
    ReviewType,
    ExpertOutput,
    CrossReviewResult,
    DiscussionPoint,
    # Matrix and descriptions
    CROSS_REVIEW_MATRIX,
    EXPERT_DESCRIPTIONS,
    # Prompt generators
    generate_cross_review_prompt,
    generate_discussion_prompt,
    generate_chairman_synthesis_prompt,
)

__all__ = [
    # Enums and data classes
    "Grade",
    "ReviewType",
    "ExpertOutput",
    "CrossReviewResult",
    "DiscussionPoint",
    # Matrix and descriptions
    "CROSS_REVIEW_MATRIX",
    "EXPERT_DESCRIPTIONS",
    # Prompt generators
    "generate_cross_review_prompt",
    "generate_discussion_prompt",
    "generate_chairman_synthesis_prompt",
]

