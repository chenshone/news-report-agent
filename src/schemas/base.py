"""基础数据模型

包含核心的评估等级、新闻条目、分析结果等基础模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Grade(str, Enum):
    """
    统一的评估等级（A/B/C/D 四级制）
    
    用于整个系统中的质量评估，包括：
    - 可信度评估
    - 相关性评估
    - 专家分析质量评估
    - 交叉评审结果
    """
    A = "A"  # 优秀：质量高，无明显问题，可直接采用
    B = "B"  # 良好：质量较好，有小问题但不影响整体
    C = "C"  # 及格：有明显问题，需要改进后才能采用
    D = "D"  # 不及格：存在严重问题，需要重新处理
    
    @classmethod
    def from_string(cls, s: str) -> "Grade":
        """从字符串解析等级"""
        if not s:
            return cls.B  # 默认 B
        s = s.upper().strip()
        if s in ("A", "A+", "A-", "优秀", "优"):
            return cls.A
        elif s in ("B", "B+", "B-", "良好", "良"):
            return cls.B
        elif s in ("C", "C+", "C-", "及格", "中"):
            return cls.C
        else:
            return cls.D
    
    @classmethod
    def from_score(cls, score: float) -> "Grade":
        """从数字分数转换为等级（兼容旧系统）"""
        if score >= 0.8:
            return cls.A
        elif score >= 0.6:
            return cls.B
        elif score >= 0.4:
            return cls.C
        else:
            return cls.D
    
    def is_passing(self) -> bool:
        """是否及格（C 及以上）"""
        return self in (Grade.A, Grade.B, Grade.C)
    
    def is_good(self) -> bool:
        """是否良好（B 及以上）"""
        return self in (Grade.A, Grade.B)
    
    def needs_attention(self) -> bool:
        """是否需要关注/讨论（C 或 D）"""
        return self in (Grade.C, Grade.D)
    
    @property
    def description(self) -> str:
        """等级描述"""
        descriptions = {
            Grade.A: "优秀",
            Grade.B: "良好",
            Grade.C: "及格",
            Grade.D: "不及格",
        }
        return descriptions[self]


# 等级类型别名
GradeType = Literal["A", "B", "C", "D"]


class GradeBreakdown(BaseModel):
    """评估等级明细"""
    model_config = ConfigDict(extra="ignore", frozen=False)

    credibility: Optional[GradeType] = None  # 可信度等级
    relevance: Optional[GradeType] = None    # 相关性等级
    quality: Optional[GradeType] = None      # 整体质量等级

    def to_dict(self) -> Dict[str, Optional[str]]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "GradeBreakdown":
        return cls.model_validate(data or {})
    
    @classmethod
    def from_scores(cls, credibility: Optional[float] = None, 
                    relevance: Optional[float] = None) -> "GradeBreakdown":
        """从旧的数字分数创建（兼容性方法）"""
        return cls(
            credibility=Grade.from_score(credibility).value if credibility is not None else None,
            relevance=Grade.from_score(relevance).value if relevance is not None else None,
        )


# 保留旧名称以保持向后兼容
ScoreBreakdown = GradeBreakdown


class NewsItem(BaseModel):
    """新闻条目"""
    model_config = ConfigDict(extra="ignore", frozen=False)

    id: str
    title: str
    url: str
    source: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    grades: GradeBreakdown = Field(default_factory=GradeBreakdown)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 保留旧名称以保持向后兼容
    @property
    def scores(self) -> GradeBreakdown:
        return self.grades

    def to_dict(self) -> Dict[str, Any]:
        # json mode ensures datetime -> ISO string
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        # 兼容旧数据格式
        if "scores" in data and "grades" not in data:
            data["grades"] = data.pop("scores")
        return cls.model_validate(data)


class AnalysisResult(BaseModel):
    """分析结果"""
    model_config = ConfigDict(extra="ignore", frozen=False)

    news_id: str
    expert_role: str
    analysis: str
    confidence_grade: Optional[GradeType] = None  # 置信度等级
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 保留旧名称以保持向后兼容
    @property
    def confidence(self) -> Optional[str]:
        return self.confidence_grade

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        # 兼容旧数据格式（数字转等级）
        if "confidence" in data and isinstance(data["confidence"], (int, float)):
            data["confidence_grade"] = Grade.from_score(data.pop("confidence")).value
        elif "confidence" in data and "confidence_grade" not in data:
            data["confidence_grade"] = data.pop("confidence")
        return cls.model_validate(data)


class IntegratedSummary(BaseModel):
    """整合摘要"""
    model_config = ConfigDict(extra="ignore", frozen=False)

    article_id: str
    title: str
    integrated_analysis: str
    references: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegratedSummary":
        return cls.model_validate(data)


__all__ = [
    "AnalysisResult",
    "Grade",
    "GradeBreakdown",
    "GradeType",
    "IntegratedSummary",
    "NewsItem",
    "ScoreBreakdown",
]

