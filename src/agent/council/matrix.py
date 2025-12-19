"""交叉评审矩阵和 Prompt 模板

定义专家之间的交叉评审关系、评审类型和 Prompt 模板。

借鉴 Andrej Karpathy 的 LLM Council 项目思想，
为异质专家（不同职责）设计的交叉评审与共识讨论机制。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReviewType(Enum):
    """评审类型"""
    ACCURACY = "accuracy"           # 准确性评审
    COMPLETENESS = "completeness"   # 完整性评审
    CONSISTENCY = "consistency"     # 一致性评审
    EVIDENCE = "evidence"           # 证据支持评审
    LOGIC = "logic"                 # 逻辑性评审


class Grade(Enum):
    """评审等级（A-D 四级制）"""
    A = "A"  # 优秀：质量高，无明显问题
    B = "B"  # 良好：质量较好，有小问题
    C = "C"  # 及格：有明显问题需要改进
    D = "D"  # 不及格：严重问题，需要重做
    
    @classmethod
    def from_string(cls, s: str) -> "Grade":
        """从字符串解析等级"""
        s = s.upper().strip()
        if s in ("A", "A+", "A-"):
            return cls.A
        elif s in ("B", "B+", "B-"):
            return cls.B
        elif s in ("C", "C+", "C-"):
            return cls.C
        else:
            return cls.D
    
    def is_passing(self) -> bool:
        """是否及格（C 及以上）"""
        return self in (Grade.A, Grade.B, Grade.C)
    
    def needs_discussion(self) -> bool:
        """是否需要触发讨论（C 或 D）"""
        return self in (Grade.C, Grade.D)


@dataclass
class ExpertOutput:
    """专家输出结果"""
    expert_name: str
    content: str
    confidence: str = "B"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossReviewResult:
    """交叉评审结果"""
    reviewer: str
    reviewee: str
    review_type: ReviewType
    grade: Grade
    issues: List[str]
    suggestions: List[str]
    agreement_points: List[str]


@dataclass
class DiscussionPoint:
    """讨论要点"""
    topic: str
    participants: List[str]
    initial_positions: Dict[str, str]
    resolution: Optional[str] = None
    consensus_reached: bool = False
    remaining_disagreements: List[str] = field(default_factory=list)


# =============================================================================
# 交叉评审矩阵 - 定义哪位专家应该评审哪位专家的哪些方面
# =============================================================================

CROSS_REVIEW_MATRIX = {
    # summarizer 被以下专家评审
    "summarizer": [
        {
            "reviewer": "fact_checker",
            "review_types": [ReviewType.ACCURACY],
            "focus": "摘要中的事实声明是否准确？关键数据是否正确？"
        },
        {
            "reviewer": "researcher",
            "review_types": [ReviewType.COMPLETENESS],
            "focus": "摘要是否遗漏了重要的背景信息或上下文？"
        },
        {
            "reviewer": "impact_assessor",
            "review_types": [ReviewType.COMPLETENESS],
            "focus": "摘要是否涵盖了影响分析所需的关键要素？"
        },
    ],
    
    # fact_checker 被以下专家评审
    "fact_checker": [
        {
            "reviewer": "researcher",
            "review_types": [ReviewType.EVIDENCE, ReviewType.COMPLETENESS],
            "focus": "核查是否涵盖所有关键声明？历史数据引用是否准确？"
        },
        {
            "reviewer": "summarizer",
            "review_types": [ReviewType.CONSISTENCY],
            "focus": "核查结果与原始摘要是否一致？是否有矛盾？"
        },
    ],
    
    # researcher 被以下专家评审
    "researcher": [
        {
            "reviewer": "fact_checker",
            "review_types": [ReviewType.ACCURACY, ReviewType.EVIDENCE],
            "focus": "背景信息是否准确？来源是否可靠？"
        },
        {
            "reviewer": "impact_assessor",
            "review_types": [ReviewType.COMPLETENESS, ReviewType.LOGIC],
            "focus": "背景是否为影响分析提供了足够支撑？历史案例是否相关？"
        },
    ],
    
    # impact_assessor 被以下专家评审
    "impact_assessor": [
        {
            "reviewer": "researcher",
            "review_types": [ReviewType.EVIDENCE, ReviewType.LOGIC],
            "focus": "影响预测是否有历史依据？推理逻辑是否合理？"
        },
        {
            "reviewer": "fact_checker",
            "review_types": [ReviewType.ACCURACY, ReviewType.LOGIC],
            "focus": "预测基于的前提是否经过验证？因果关系是否成立？"
        },
    ],
}


# =============================================================================
# 专家描述
# =============================================================================

EXPERT_DESCRIPTIONS = {
    "summarizer": "你专注于提取核心要点和生成结构化摘要，擅长信息压缩和关键信息识别。",
    "fact_checker": "你专注于核查事实声明的真实性，擅长信息溯源和证据验证。",
    "researcher": "你专注于补充背景信息和关联历史事件，擅长构建完整的上下文。",
    "impact_assessor": "你专注于评估影响和预测趋势，擅长多维度分析和前瞻性判断。",
}


# =============================================================================
# Prompt 模板
# =============================================================================

CROSS_REVIEW_PROMPT_TEMPLATE = """你是 {reviewer_name}，现在需要从你的专业角度评审 {reviewee_name} 的分析结果。

## 你的专业职责
{reviewer_description}

## 评审重点
{review_focus}

## 待评审内容

### {reviewee_name} 的分析结果：
{reviewee_output}

### 原始分析主题/素材：
{original_context}

---

## 评审要求

请从以下维度进行评审：

### 1. 准确性评估
- 内容中的事实声明是否准确？
- 数据、日期、人物等是否正确？

### 2. 完整性评估
- 是否遗漏了重要信息？
- 分析角度是否全面？

### 3. 一致性评估
- 与你的分析是否有矛盾之处？
- 逻辑是否自洽？

### 4. 建议与改进
- 需要补充或修正什么？
- 有什么可以做得更好？

---

## 评审等级说明（A/B/C/D 四级制）

| 等级 | 含义 | 标准 |
|------|------|------|
| **A** | 优秀 | 质量高，无明显问题，可直接采用 |
| **B** | 良好 | 质量较好，有小问题但不影响整体 |
| **C** | 及格 | 有明显问题，需要改进后才能采用 |
| **D** | 不及格 | 存在严重问题，需要重新分析 |

---

## 输出格式

请以 JSON 格式输出评审结果：

```json
{{
  "overall_grade": "B",
  "grades": {{
    "accuracy": "A",
    "completeness": "B",
    "consistency": "B",
    "logic": "A"
  }},
  "issues": [
    {{
      "severity": "high/medium/low",
      "description": "具体问题描述",
      "location": "问题出现的位置/段落"
    }}
  ],
  "agreement_points": [
    "认同的观点1",
    "认同的观点2"
  ],
  "suggestions": [
    "改进建议1",
    "改进建议2"
  ],
  "conflicts_with_my_analysis": [
    {{
      "topic": "冲突主题",
      "their_position": "对方观点",
      "my_position": "我的观点",
      "evidence": "我的依据"
    }}
  ]
}}
```
"""


CONSENSUS_DISCUSSION_PROMPT = """你是 {expert_name}，现在需要参与专家讨论以解决以下分歧。

## 讨论主题
{discussion_topic}

## 分歧描述
{conflict_description}

## 各方立场

{positions}

## 你的任务

作为 {expert_name}，请：

1. **重新审视你的立场**
2. **提供补充论证或修正**
3. **寻求共识**

---

## 输出格式

```json
{{
  "updated_position": "修正后的立场或重申原立场",
  "reasoning": "你的论证过程",
  "concessions": ["认可对方的哪些观点"],
  "remaining_disagreements": ["仍然不同意的点"],
  "proposed_resolution": "建议的解决方案",
  "confidence": "B"
}}
```
"""


CHAIRMAN_SYNTHESIS_PROMPT = """你是专家委员会主管（Chairman），需要综合所有专家的分析和讨论，形成最终结论。

## 原始分析任务
{original_task}

---

## 阶段1：各专家独立分析结果

{expert_outputs}

---

## 阶段2：交叉评审结果

### 评审汇总
{cross_review_summary}

### 发现的主要问题
{identified_issues}

### 专家间的分歧点
{conflicts}

---

## 阶段3：共识讨论结果

{discussion_results}

---

## 你的任务

1. 综合评估各专家的分析质量
2. 对仍存在分歧的问题做出裁决
3. 生成整合报告

使用 Markdown 格式输出。
"""


# =============================================================================
# Prompt 生成函数
# =============================================================================

def generate_cross_review_prompt(
    reviewer: str,
    reviewee: str,
    reviewee_output: str,
    original_context: str,
    review_focus: str,
) -> str:
    """生成交叉评审的 Prompt"""
    return CROSS_REVIEW_PROMPT_TEMPLATE.format(
        reviewer_name=reviewer,
        reviewee_name=reviewee,
        reviewer_description=EXPERT_DESCRIPTIONS.get(reviewer, ""),
        review_focus=review_focus,
        reviewee_output=reviewee_output,
        original_context=original_context,
    )


def generate_discussion_prompt(
    expert_name: str,
    discussion_topic: str,
    conflict_description: str,
    positions: Dict[str, str],
) -> str:
    """生成共识讨论的 Prompt"""
    positions_text = "\n".join([
        f"**{expert}**: {position}" 
        for expert, position in positions.items()
    ])
    
    return CONSENSUS_DISCUSSION_PROMPT.format(
        expert_name=expert_name,
        discussion_topic=discussion_topic,
        conflict_description=conflict_description,
        positions=positions_text,
    )


def generate_chairman_synthesis_prompt(
    original_task: str,
    expert_outputs: Dict[str, str],
    cross_review_summary: str,
    identified_issues: List[str],
    conflicts: List[Dict[str, str]],
    discussion_results: str,
) -> str:
    """生成主管综合裁决的 Prompt"""
    expert_outputs_text = "\n\n".join([
        f"### {expert}\n{output}"
        for expert, output in expert_outputs.items()
    ])
    
    issues_text = "\n".join([f"- {issue}" for issue in identified_issues])
    
    conflicts_text = "\n".join([
        f"- **{c.get('topic', '未知主题')}**: {c.get('description', '')}"
        for c in conflicts
    ])
    
    return CHAIRMAN_SYNTHESIS_PROMPT.format(
        original_task=original_task,
        expert_outputs=expert_outputs_text,
        cross_review_summary=cross_review_summary,
        identified_issues=issues_text if issues_text else "无重大问题",
        conflicts=conflicts_text if conflicts_text else "无明显分歧",
        discussion_results=discussion_results if discussion_results else "专家已达成共识",
    )


__all__ = [
    "Grade",
    "ReviewType",
    "ExpertOutput",
    "CrossReviewResult",
    "DiscussionPoint",
    "CROSS_REVIEW_MATRIX",
    "EXPERT_DESCRIPTIONS",
    "generate_cross_review_prompt",
    "generate_discussion_prompt",
    "generate_chairman_synthesis_prompt",
]

