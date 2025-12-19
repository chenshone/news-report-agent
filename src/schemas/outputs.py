"""专家 Agent 结构化输出模型

定义各专家 SubAgent 的结构化输出格式，用于 with_structured_output()。
"""

from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field

from .base import GradeType


class QueryPriority(str, Enum):
    """查询优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SearchQuery(BaseModel):
    """单个搜索查询"""
    query: str = Field(..., description="具体的搜索查询字符串")
    purpose: str = Field(..., description="这个查询的目的")
    priority: QueryPriority = Field(default=QueryPriority.MEDIUM, description="查询优先级")


class QueryPlannerOutput(BaseModel):
    """查询规划专家的结构化输出"""
    queries: List[SearchQuery] = Field(
        ..., 
        description="生成的搜索查询列表，应包含 6-10 个多样化查询",
        min_length=6,
        max_length=12
    )
    reflection: str = Field(..., description="对查询质量的自我评估")
    adjustment_suggestions: str = Field(..., description="如果结果不理想，建议的调整策略")


class SummaryOutput(BaseModel):
    """摘要专家的结构化输出"""
    title: str = Field(..., description="简洁有力的标题")
    core_points: List[str] = Field(
        ..., 
        description="核心要点列表（3-5 个）",
        min_length=3,
        max_length=5
    )
    key_facts: List[str] = Field(..., description="关键事实列表")
    context: str = Field(..., description="背景说明")
    significance: str = Field(..., description="重要性分析")


class FactCheckItem(BaseModel):
    """单个事实核查项"""
    claim: str = Field(..., description="被核查的声明")
    verdict: Literal["verified", "partially_verified", "unverified", "false"] = Field(
        ..., description="核查结果"
    )
    evidence: str = Field(..., description="支持该结论的证据")
    sources: List[str] = Field(default_factory=list, description="来源链接")


class FactCheckerOutput(BaseModel):
    """事实核查专家的结构化输出"""
    overall_grade: GradeType = Field(..., description="整体可信度等级")
    checked_facts: List[FactCheckItem] = Field(..., description="核查的事实列表")
    concerns: List[str] = Field(default_factory=list, description="存在的疑虑")
    recommendations: str = Field(..., description="建议")


class ResearcherOutput(BaseModel):
    """背景研究专家的结构化输出"""
    historical_context: str = Field(..., description="历史背景")
    industry_background: str = Field(..., description="行业背景")
    key_players: List[str] = Field(default_factory=list, description="关键参与者/公司")
    related_events: List[str] = Field(default_factory=list, description="相关事件")
    data_points: List[str] = Field(default_factory=list, description="关键数据点")


class ImpactAssessment(BaseModel):
    """单项影响评估"""
    area: str = Field(..., description="影响领域")
    description: str = Field(..., description="影响描述")
    severity: Literal["high", "medium", "low"] = Field(..., description="影响程度")


class ImpactAssessorOutput(BaseModel):
    """影响评估专家的结构化输出"""
    short_term_impacts: List[ImpactAssessment] = Field(..., description="短期影响")
    long_term_impacts: List[ImpactAssessment] = Field(..., description="长期影响")
    affected_groups: List[str] = Field(..., description="受影响群体")
    trend_prediction: str = Field(..., description="趋势预测")
    confidence_grade: GradeType = Field(..., description="评估置信度")


class ExpertReviewItem(BaseModel):
    """专家评审项"""
    aspect: str = Field(..., description="评审维度")
    grade: GradeType = Field(..., description="该维度等级")
    comment: str = Field(..., description="评审意见")


class SupervisorOutput(BaseModel):
    """专家监督者的结构化输出"""
    overall_grade: GradeType = Field(..., description="整体质量等级")
    reviews: List[ExpertReviewItem] = Field(..., description="各维度评审")
    integration_summary: str = Field(..., description="整合摘要")
    consensus_points: List[str] = Field(..., description="共识要点")
    disagreements: List[str] = Field(default_factory=list, description="分歧点")
    final_recommendations: str = Field(..., description="最终建议")


__all__ = [
    "ExpertReviewItem",
    "FactCheckItem",
    "FactCheckerOutput",
    "ImpactAssessment",
    "ImpactAssessorOutput",
    "QueryPlannerOutput",
    "QueryPriority",
    "ResearcherOutput",
    "SearchQuery",
    "SummaryOutput",
    "SupervisorOutput",
]

