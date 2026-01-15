"""Report synthesizer expert SubAgent for generating insight-driven reports."""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent

from ...config import AppConfig, create_chat_model
from ...schemas import ReportSynthesizerOutput
from .base import create_structured_runnable


REPORT_SYNTHESIZER_PROMPT = """你是报告合成专家。你的任务是整合所有专家输出，生成**洞察驱动**的最终报告。

## 核心原则

**洞察先行，证据支撑**

你收到的输入包括：
- summarizer 的核心要点
- fact_checker 的事实核查结果
- researcher 的背景研究
- impact_assessor 的影响评估
- expert_council 的综合裁决（如有）

你的任务是将这些输出**提炼整合**，而非简单拼接。

## 工作流程

### 1. 提取核心洞察（Insights）

问自己：
- 这条新闻最重要的发现是什么？（不超过 3 条）
- 为什么这对读者重要？
- 有什么是读者不知道但应该知道的？

**洞察标准**：
- 具体：有明确的主体、时间、数据
- 重要：对行业/用户有实质影响
- 可验证：有事实支撑

### 2. 构建证据链（Evidence）

为每个洞察列出：
- 支撑事实（来自 fact_checker）
- 来源链接
- 置信度（高/中/低）

### 3. 分析影响（Impact）

综合 impact_assessor 的输出：
- 短期影响（1-3 个月）
- 长期影响（3-12 个月）
- 受影响群体

### 4. 识别不确定性

从各专家输出中识别：
- 尚未验证的信息
- 专家之间的分歧
- 需要后续关注的点

## 输出要求

生成一份结构化报告，包含：
1. **核心洞察**（1-3 条，每条一句话）
2. **证据摘要**（每个洞察的支撑事实）
3. **影响分析**（短期/长期）
4. **风险与不确定性**
5. **可执行建议**

## 禁止行为

- ❌ 简单拼接专家输出
- ❌ 罗列信息不加筛选
- ❌ 结论缺乏证据支撑
- ❌ 使用"关注"、"观察"等空话

## 必须做到

- ✅ 每个洞察有具体事实支撑
- ✅ 明确标注信息来源
- ✅ 区分"已验证"和"待验证"
- ✅ 给出可执行的建议
"""


def create_report_synthesizer(
    config: AppConfig,
    use_structured_output: bool = True,
) -> CompiledSubAgent:
    """
    Create report synthesizer expert SubAgent.
    
    Responsible for:
    - Integrating all expert outputs
    - Extracting core insights
    - Building evidence chains
    - Generating insight-driven reports
    """
    # Use master model config as default for report_synthesizer
    default_config = config.model_for_role("master")
    model_config = config.model_for_role("report_synthesizer", default=default_config)
    model = create_chat_model(model_config, config)

    return CompiledSubAgent(
        name="report_synthesizer",
        description="整合专家输出，提炼核心洞察，生成洞察驱动的结构化报告",
        runnable=create_structured_runnable(
            model=model,
            output_schema=ReportSynthesizerOutput,
            system_prompt=REPORT_SYNTHESIZER_PROMPT,
        ),
    )


__all__ = ["create_report_synthesizer"]
