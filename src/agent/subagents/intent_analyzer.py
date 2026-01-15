"""Intent Analyzer SubAgent for understanding user queries.

Analyzes user queries to extract intent, time range, domain, and interests
before generating a search plan for user confirmation.
"""

from __future__ import annotations

from deepagents.middleware.subagents import CompiledSubAgent

from ...config import AppConfig, create_chat_model
from ...schemas import IntentAnalysis
from ..subagents.base import create_structured_runnable

INTENT_ANALYZER_PROMPT = """你是一个查询意图分析专家。你的任务是分析用户的查询请求，提取关键信息以便后续搜索。

## 分析维度

1. **时间理解**
   - 解析用户提到的时间词（今天、近期、最新、本周等）
   - 转换为具体的天数范围
   - 默认：如果没有明确时间，使用 7 天

2. **领域识别**
   - 提取领域关键词（如 AI、区块链、医疗等）
   - 识别具体技术/产品名称
   - 分类到预定义类别

3. **关注点推断**
   - 从查询中推断用户可能感兴趣的角度：
     - 技术突破（新技术、新方法）
     - 产品发布（新功能、新版本）
     - 融资新闻（投资、收购）
     - 开源项目（GitHub、工具）
     - 政策法规（监管、标准）
     - 行业动态（合作、竞争）

4. **深度建议**
   - 快速概览（quick）：5-10分钟，重点摘要
   - 深度报告（deep）：15-30分钟，详细分析

5. **需要澄清的问题**
   - 如果查询模糊，列出需要用户确认的问题
   - 最多 3 个最重要的问题

## 输出要求

返回结构化的 IntentAnalysis 对象，包含：
- original_query: 原始查询
- understood_query: 你理解的查询意图（用一句话描述）
- time_range_description: 时间范围描述
- time_range_days: 时间范围天数
- domain_keywords: 领域关键词列表
- domain_category: 领域分类（如 AI, tech, finance, health, general）
- possible_interests: 可能的关注点列表
- suggested_depth: 建议深度 (quick/deep)
- estimated_time_minutes: 预估完成时间
- clarification_questions: 需要确认的问题（如果有）

## 示例

用户查询: "最近 AI Agent 领域有什么进展"

分析结果:
- understood_query: "近期 AI Agent 技术和产品领域的最新发展动态"
- time_range_description: "最近 7 天"
- time_range_days: 7
- domain_keywords: ["AI Agent", "自主代理", "工具调用", "多智能体"]
- domain_category: "AI"
- possible_interests: ["技术突破", "开源项目", "产品发布"]
- suggested_depth: "deep"
- estimated_time_minutes: 15
- clarification_questions: ["您更关注哪个方向？技术/产品/开源？", "有特别想了解的公司或项目吗？"]
"""


def create_intent_analyzer(config: AppConfig) -> CompiledSubAgent:
    """Create the intent analyzer subagent.
    
    Args:
        config: Application configuration.
        
    Returns:
        Configured intent analyzer subagent.
    """
    model_config = config.model_for_role("master")
    model = create_chat_model(model_config, config)

    return CompiledSubAgent(
        name="intent_analyzer",
        description="分析用户查询意图，提取时间范围、领域关键词、关注点，生成结构化的意图分析结果",
        runnable=create_structured_runnable(
            model=model,
            output_schema=IntentAnalysis,
            system_prompt=INTENT_ANALYZER_PROMPT,
        ),
    )


__all__ = ["create_intent_analyzer", "INTENT_ANALYZER_PROMPT"]
