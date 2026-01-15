"""Query understanding schemas for intent analysis and search planning.

Provides structured models for the user query understanding phase,
enabling human-in-the-loop confirmation before execution.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SearchDirection(BaseModel):
    """A planned search direction with source and purpose."""

    source: str = Field(..., description="信息源（如 internet_search, search_arxiv, search_hackernews）")
    query_template: str = Field(..., description="具体的搜索查询")
    purpose: str = Field(..., description="这个搜索方向的目的")
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="搜索优先级"
    )
    tool_params: str = Field(
        default="{}", description="工具特定参数的 JSON 字符串（如 max_results, categories）"
    )


class IntentAnalysis(BaseModel):
    """Analysis of user query intent."""

    original_query: str = Field(..., description="用户原始查询")
    understood_query: str = Field(..., description="系统理解的查询意图")
    
    # Time understanding
    time_range_description: str = Field(..., description="时间范围描述（如：最近7天）")
    time_range_days: int = Field(
        default=7, ge=1, le=365, description="时间范围（天数）"
    )
    
    # Domain understanding
    domain_keywords: List[str] = Field(
        default_factory=list, description="识别到的领域关键词"
    )
    domain_category: str = Field(
        default="general", description="领域分类（如 AI, tech, finance）"
    )
    
    # Interest inference
    possible_interests: List[str] = Field(
        default_factory=list,
        description="推断的可能关注点（如：技术突破、产品发布、融资、开源项目）",
    )
    
    # Depth preference
    suggested_depth: Literal["quick", "deep"] = Field(
        default="deep", description="建议的分析深度"
    )
    estimated_time_minutes: int = Field(
        default=10, description="预估完成时间（分钟）"
    )
    
    # Clarifications needed
    clarification_questions: List[str] = Field(
        default_factory=list, description="需要用户确认的问题"
    )


class SearchPlan(BaseModel):
    """A complete search plan for user confirmation."""

    intent: IntentAnalysis = Field(..., description="意图解析结果")
    
    # Search directions
    included_directions: List[SearchDirection] = Field(
        ..., description="计划执行的搜索方向"
    )
    excluded_directions: List[str] = Field(
        default_factory=list, description="排除的搜索方向（及原因）"
    )
    
    # User exclusions
    excluded_topics: List[str] = Field(
        default_factory=list, description="用户已知/不感兴趣的主题"
    )
    excluded_sources: List[str] = Field(
        default_factory=list, description="排除的信息源"
    )
    
    # Estimates
    total_estimated_queries: int = Field(
        default=10, description="计划执行的搜索查询总数"
    )
    estimated_time_minutes: int = Field(
        default=10, description="预估总耗时（分钟）"
    )


class UserConfirmation(BaseModel):
    """User's confirmation and adjustments to the search plan."""

    approved: bool = Field(..., description="是否批准执行")
    
    # Interest selection
    selected_interests: List[str] = Field(
        default_factory=list, description="用户选择的关注点"
    )
    
    # Exclusions
    excluded_topics: List[str] = Field(
        default_factory=list, description="用户要排除的主题（如已知内容）"
    )
    excluded_sources: List[str] = Field(
        default_factory=list, description="用户要排除的信息源"
    )
    
    # Depth preference
    depth_preference: Literal["quick", "deep"] = Field(
        default="deep", description="分析深度偏好"
    )
    
    # Additional notes
    additional_context: str = Field(
        default="", description="用户提供的额外背景或要求"
    )
    specific_questions: List[str] = Field(
        default_factory=list, description="用户特别想了解的问题"
    )


class ExecutionPlan(BaseModel):
    """Final execution plan after user confirmation."""

    original_query: str = Field(..., description="原始用户查询")
    search_plan: SearchPlan = Field(..., description="确认后的搜索计划")
    user_confirmation: UserConfirmation = Field(..., description="用户确认内容")
    
    # Computed final plan
    final_search_directions: List[SearchDirection] = Field(
        ..., description="最终要执行的搜索方向"
    )
    analysis_depth: Literal["quick", "deep"] = Field(..., description="最终分析深度")
    
    # Skip confirmation flag (for quick mode)
    skipped_confirmation: bool = Field(
        default=False, description="是否跳过了确认步骤"
    )


__all__ = [
    "SearchDirection",
    "IntentAnalysis",
    "SearchPlan",
    "UserConfirmation",
    "ExecutionPlan",
]
