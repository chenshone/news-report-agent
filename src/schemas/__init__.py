"""数据模型定义

包含所有 Pydantic 模型，分为：
- base: 基础模型（Grade, NewsItem, AnalysisResult 等）
- outputs: 专家输出模型（QueryPlannerOutput, SummaryOutput 等）
- query_understanding: 查询理解模型（IntentAnalysis, SearchPlan 等）
"""

from .base import (
    AnalysisResult,
    Grade,
    GradeBreakdown,
    GradeType,
    IntegratedSummary,
    NewsItem,
    ScoreBreakdown,
)
from .outputs import (
    ExpertReviewItem,
    FactCheckItem,
    FactCheckerOutput,
    ImpactAssessment,
    ImpactAssessorOutput,
    InsightItem,
    QueryPlannerOutput,
    QueryPriority,
    ReportSynthesizerOutput,
    ResearcherOutput,
    SearchQuery,
    SummaryOutput,
    SupervisorOutput,
)
from .query_understanding import (
    ExecutionPlan,
    IntentAnalysis,
    SearchDirection,
    SearchPlan,
    UserConfirmation,
)

__all__ = [
    # base
    "AnalysisResult",
    "Grade",
    "GradeBreakdown",
    "GradeType",
    "IntegratedSummary",
    "NewsItem",
    "ScoreBreakdown",
    # outputs
    "ExpertReviewItem",
    "FactCheckItem",
    "FactCheckerOutput",
    "ImpactAssessment",
    "ImpactAssessorOutput",
    "InsightItem",
    "QueryPlannerOutput",
    "QueryPriority",
    "ReportSynthesizerOutput",
    "ResearcherOutput",
    "SearchQuery",
    "SummaryOutput",
    "SupervisorOutput",
    # query_understanding
    "ExecutionPlan",
    "IntentAnalysis",
    "SearchDirection",
    "SearchPlan",
    "UserConfirmation",
]
