"""Expert council SubAgent for multi-stage expert collaboration.

Stages (stage 1 provided externally):
1. Independent analysis - Expert outputs pre-provided
2. Cross-review - Experts evaluate each other
3. Consensus discussion - Handle disagreements
4. Chairman synthesis - Final verdict
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from deepagents.middleware.subagents import CompiledSubAgent
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda

from ..council import (
    CROSS_REVIEW_MATRIX,
    EXPERT_DESCRIPTIONS,
    generate_cross_review_prompt,
)
from ...config import AppConfig, create_chat_model
from ...prompts.experts import (
    EXPERT_SUPERVISOR_PROMPT,
    FACT_CHECKER_PROMPT,
    IMPACT_ASSESSOR_PROMPT,
    RESEARCHER_PROMPT,
    SUMMARIZER_PROMPT,
)


_EXPERT_PROMPTS = {
    "summarizer": SUMMARIZER_PROMPT,
    "fact_checker": FACT_CHECKER_PROMPT,
    "researcher": RESEARCHER_PROMPT,
    "impact_assessor": IMPACT_ASSESSOR_PROMPT,
    "expert_supervisor": EXPERT_SUPERVISOR_PROMPT,
}

_EXPECTED_EXPERTS = ("summarizer", "fact_checker", "researcher", "impact_assessor")

_GRADE_VALUES = {"A": 4, "B": 3, "C": 2, "D": 1}


def _parse_json_payload(raw: str) -> dict[str, Any] | None:
    """Parse JSON from raw text, handling code blocks."""
    candidates: list[str] = []
    stripped = raw.strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)

    for match in re.finditer(r"```(?:json)?\n(.*?)```", raw, re.S):
        candidates.append(match.group(1).strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue

    return None


def _extract_expert_payload(raw: str) -> tuple[str, str, dict[str, str]] | None:
    """Extract task, context, and expert outputs from raw input."""
    payload = _parse_json_payload(raw)
    if not payload:
        return None

    expert_outputs = payload.get("expert_outputs")
    if expert_outputs is None:
        expert_outputs = {
            key: payload.get(key)
            for key in _EXPECTED_EXPERTS
            if payload.get(key)
        }

    if not isinstance(expert_outputs, dict) or not expert_outputs:
        return None

    normalized_outputs = {
        key: str(value)
        for key, value in expert_outputs.items()
        if value is not None
    }

    if not normalized_outputs:
        return None

    task = (
        payload.get("task")
        or payload.get("analysis_task")
        or "执行专家委员会分析"
    )
    context = (
        payload.get("context")
        or payload.get("news_pack")
        or payload.get("input")
        or ""
    )

    return task, context, normalized_outputs


def _extract_grade(text: str) -> str:
    """Extract grade (A/B/C/D) from text."""
    json_match = re.search(r'"overall_grade"\s*:\s*"([ABCD])"', text, re.IGNORECASE)
    if json_match:
        return json_match.group(1).upper()

    grade_match = re.search(r'等级[：:]\s*([ABCD])', text, re.IGNORECASE)
    if grade_match:
        return grade_match.group(1).upper()

    return "B"


def _calculate_average_grade(grades: list[str]) -> str:
    """Calculate average grade from a list of grades."""
    if not grades:
        return "B"

    avg = sum(_GRADE_VALUES.get(g, 3) for g in grades) / len(grades)

    if avg >= 3.5:
        return "A"
    if avg >= 2.5:
        return "B"
    if avg >= 1.5:
        return "C"
    return "D"


class ExpertCouncilRunner:
    """Expert council executor for review and verdict workflow."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.expert_models = {
            "summarizer": create_chat_model(config.model_for_role("summarizer"), config),
            "fact_checker": create_chat_model(config.model_for_role("fact_checker"), config),
            "researcher": create_chat_model(config.model_for_role("researcher"), config),
            "impact_assessor": create_chat_model(config.model_for_role("impact_assessor"), config),
            "expert_supervisor": create_chat_model(config.model_for_role("master"), config),
        }

    async def run_council(
        self,
        task: str,
        context: str,
        expert_outputs: dict[str, str],
    ) -> str:
        """Execute expert council workflow."""
        if not expert_outputs:
            return "未提供专家输出，无法进行交叉评审。"

        report_parts = [
            "# 专家委员会分析报告\n",
            f"**分析任务**: {task}\n",
        ]

        # Stage 1: Independent analysis (provided)
        report_parts.append("\n---\n## 阶段 1: 独立分析（已提供）\n")
        missing_experts = [e for e in _EXPECTED_EXPERTS if e not in expert_outputs]
        if missing_experts:
            report_parts.append(f"缺少专家输出: {', '.join(missing_experts)}\n")

        for expert in _EXPECTED_EXPERTS:
            if expert in expert_outputs:
                output = expert_outputs[expert]
                preview = output[:500] + "..." if len(output) > 500 else output
                report_parts.append(f"\n### {expert}\n{preview}\n")

        # Stage 2: Cross-review
        report_parts.append("\n---\n## 阶段 2: 交叉评审\n")
        reviews, grade_summary = await self._stage2_cross_review(expert_outputs, context)

        report_parts.append("\n### 评审等级汇总\n")
        for reviewee, grades in grade_summary.items():
            avg_grade = _calculate_average_grade(grades)
            report_parts.append(f"- **{reviewee}**: {avg_grade} (来自 {len(grades)} 位评审)\n")

        conflicts = self._identify_conflicts(reviews)

        # Stage 3: Consensus discussion
        report_parts.append("\n---\n## 阶段 3: 共识讨论\n")
        if conflicts:
            report_parts.append(f"发现 {len(conflicts)} 个需要讨论的分歧点\n")
            discussion_results = await self._stage3_consensus_discussion(conflicts)
            report_parts.append(discussion_results)
        else:
            report_parts.append("专家意见基本一致，无需额外讨论\n")
            discussion_results = ""

        # Stage 4: Chairman synthesis
        report_parts.append("\n---\n## 阶段 4: 主管综合裁决\n")
        final_synthesis = await self._stage4_chairman_synthesis(
            task, expert_outputs, grade_summary, conflicts, discussion_results
        )
        report_parts.append(final_synthesis)

        return "\n".join(report_parts)

    async def _stage2_cross_review(
        self, expert_outputs: dict[str, str], context: str
    ) -> tuple[list[dict], dict[str, list[str]]]:
        """Stage 2: Cross-review between experts."""

        async def do_review(reviewer: str, reviewee: str, focus: str) -> dict:
            model = self.expert_models[reviewer]
            prompt = generate_cross_review_prompt(
                reviewer=reviewer,
                reviewee=reviewee,
                reviewee_output=expert_outputs.get(reviewee, ""),
                original_context=context[:1000],
                review_focus=focus,
            )
            messages = [
                {"role": "system", "content": EXPERT_DESCRIPTIONS.get(reviewer, "")},
                {"role": "user", "content": prompt},
            ]
            try:
                response = await model.ainvoke(messages)
                return {
                    "reviewer": reviewer,
                    "reviewee": reviewee,
                    "grade": _extract_grade(response.content),
                    "content": response.content,
                }
            except Exception as e:
                return {
                    "reviewer": reviewer,
                    "reviewee": reviewee,
                    "grade": "C",
                    "content": f"评审失败: {e}",
                }

        review_tasks = []
        for reviewee, reviewer_configs in CROSS_REVIEW_MATRIX.items():
            if reviewee not in expert_outputs:
                continue
            for cfg in reviewer_configs:
                reviewer = cfg["reviewer"]
                if reviewer in expert_outputs:
                    review_tasks.append(do_review(reviewer, reviewee, cfg["focus"]))

        results = await asyncio.gather(*review_tasks)

        reviews = list(results)
        grade_summary: dict[str, list[str]] = {}
        for result in results:
            reviewee = result["reviewee"]
            grade_summary.setdefault(reviewee, []).append(result["grade"])

        return reviews, grade_summary

    def _identify_conflicts(self, reviews: list[dict]) -> list[dict]:
        """Identify disagreements requiring discussion."""
        return [
            {
                "topic": f"{r['reviewer']} 对 {r['reviewee']} 的评审",
                "grade": r.get("grade", "B"),
                "reviewer": r["reviewer"],
                "reviewee": r["reviewee"],
                "content": r.get("content", "")[:300],
            }
            for r in reviews
            if r.get("grade", "B") in ("C", "D")
        ]

    async def _stage3_consensus_discussion(self, conflicts: list[dict]) -> str:
        """Stage 3: Consensus discussion for conflicts."""
        if not conflicts:
            return "无需讨论"

        discussions = []
        for conflict in conflicts[:3]:
            reviewee = conflict["reviewee"]
            reviewer = conflict["reviewer"]
            model = self.expert_models.get(reviewee)
            if not model:
                continue

            prompt = f"""你是 {reviewee}，你的分析被 {reviewer} 评为 {conflict['grade']} 级。

{reviewer} 的评审意见:
{conflict['content']}

请针对这些意见进行回应（200字内）。
"""
            try:
                response = await model.ainvoke([{"role": "user", "content": prompt}])
                discussions.extend([
                    f"\n### 分歧: {conflict['topic']}\n",
                    f"**评审等级**: {conflict['grade']}\n",
                    f"**{reviewee} 的回应**:\n{response.content}\n",
                ])
            except Exception as e:
                discussions.extend([
                    f"\n### 分歧: {conflict['topic']}\n",
                    f"讨论失败: {e}\n",
                ])

        return "\n".join(discussions)

    async def _stage4_chairman_synthesis(
        self,
        task: str,
        expert_outputs: dict[str, str],
        grade_summary: dict[str, list[str]],
        conflicts: list[dict],
        discussion_results: str,
    ) -> str:
        """Stage 4: Chairman final synthesis."""
        model = self.expert_models["expert_supervisor"]

        expert_text = "\n\n".join(
            f"### {name}\n{output[:800]}..." if len(output) > 800 else f"### {name}\n{output}"
            for name, output in expert_outputs.items()
        )

        review_text = "\n".join(
            f"- {reviewee}: 平均等级 {_calculate_average_grade(grades)}"
            for reviewee, grades in grade_summary.items()
        )

        conflict_text = (
            "\n".join(f"- {c['topic']}: 等级 {c['grade']}" for c in conflicts)
            if conflicts
            else "无明显分歧"
        )

        prompt = f"""你是专家委员会主席，需要综合所有专家的分析做最终裁决。

## 原始任务
{task}

## 各专家独立分析
{expert_text}

## 交叉评审结果
{review_text}

## 分歧点
{conflict_text}

## 讨论结果
{discussion_results or "专家意见一致，未进行讨论"}

---

请生成最终的综合裁决报告，使用 Markdown 格式。
"""

        try:
            messages = [
                {"role": "system", "content": _EXPERT_PROMPTS["expert_supervisor"]},
                {"role": "user", "content": prompt},
            ]
            response = await model.ainvoke(messages)
            return response.content
        except Exception as e:
            return f"主管综合失败: {e}"


def _prepare_council_state(state: dict) -> tuple[str, str, dict[str, str] | None, list]:
    """Extract and normalize state for council execution."""
    messages = state.get("messages", [])
    expert_outputs = state.get("expert_outputs")
    task = state.get("task") or state.get("analysis_task") or "执行专家委员会分析"
    context = state.get("context") or state.get("news_pack") or ""

    if isinstance(expert_outputs, dict):
        expert_outputs = {
            key: str(value)
            for key, value in expert_outputs.items()
            if value is not None
        }
    else:
        expert_outputs = None

    if not expert_outputs and messages:
        last_message = messages[-1]
        task_content = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )
        payload = _extract_expert_payload(task_content)
        if payload:
            task, context, expert_outputs = payload

    return task, context, expert_outputs, messages


def _build_missing_output_response(messages: list) -> dict:
    """Build response for missing expert outputs."""
    missing_hint = "、".join(_EXPECTED_EXPERTS)
    return {
        "messages": [
            *messages,
            AIMessage(
                content=(
                    "未提供专家输出，无法进行交叉评审。请传入 JSON，包含 task/context "
                    f"以及 expert_outputs（{missing_hint}）。"
                )
            ),
        ]
    }


def create_council(config: AppConfig) -> CompiledSubAgent:
    """Create expert council SubAgent."""
    runner = ExpertCouncilRunner(config)

    def invoke_fn(state: dict, config_: RunnableConfig | None = None) -> dict:
        """Synchronous invocation."""
        task, context, expert_outputs, messages = _prepare_council_state(state)

        if not messages:
            return {"messages": [AIMessage(content="未提供分析任务")]}

        if not expert_outputs:
            return _build_missing_output_response(messages)

        try:
            result = asyncio.run(
                runner.run_council(task=task, context=context, expert_outputs=expert_outputs)
            )
        except Exception as e:
            result = f"专家委员会执行失败: {e}"

        return {"messages": [*messages, AIMessage(content=result)]}

    async def ainvoke_fn(state: dict, config_: RunnableConfig | None = None) -> dict:
        """Asynchronous invocation."""
        task, context, expert_outputs, messages = _prepare_council_state(state)

        if not messages:
            return {"messages": [AIMessage(content="未提供分析任务")]}

        if not expert_outputs:
            return _build_missing_output_response(messages)

        try:
            result = await runner.run_council(
                task=task, context=context, expert_outputs=expert_outputs
            )
        except Exception as e:
            result = f"专家委员会执行失败: {e}"

        return {"messages": [*messages, AIMessage(content=result)]}

    return CompiledSubAgent(
        name="expert_council",
        description=(
            "基于已有专家输出执行交叉评审、共识讨论、主管综合。"
            "调用前需提供 summarizer/fact_checker/researcher/impact_assessor 输出。"
        ),
        runnable=RunnableLambda(invoke_fn, afunc=ainvoke_fn),
    )


__all__ = ["create_council", "ExpertCouncilRunner"]
