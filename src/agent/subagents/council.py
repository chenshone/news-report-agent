"""专家委员会 SubAgent

封装专家协作流程（阶段1由外部提供）：
1. 独立分析 - 各专家输出已预先提供
2. 交叉评审 - 专家互评
3. 共识讨论 - 处理分歧
4. 主管综合 - 最终裁决
"""

import asyncio
import json
import re
from typing import Any, Dict, List

from deepagents.middleware.subagents import CompiledSubAgent
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda

from ...config import AppConfig, create_chat_model
from ...prompts.experts import (
    SUMMARIZER_PROMPT,
    FACT_CHECKER_PROMPT,
    RESEARCHER_PROMPT,
    IMPACT_ASSESSOR_PROMPT,
    EXPERT_SUPERVISOR_PROMPT,
)
from ..council import CROSS_REVIEW_MATRIX, EXPERT_DESCRIPTIONS, generate_cross_review_prompt


# 专家系统提示词（复用 experts.py 中的原始 prompt，避免循环导入）
_EXPERT_PROMPTS = {
    "summarizer": SUMMARIZER_PROMPT,
    "fact_checker": FACT_CHECKER_PROMPT,
    "researcher": RESEARCHER_PROMPT,
    "impact_assessor": IMPACT_ASSESSOR_PROMPT,
    "expert_supervisor": EXPERT_SUPERVISOR_PROMPT,
}

_EXPECTED_EXPERTS = ("summarizer", "fact_checker", "researcher", "impact_assessor")


def _parse_json_payload(raw: str) -> Dict[str, Any] | None:
    candidates: list[str] = []
    stripped = raw.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)

    for match in re.finditer(r"```(?:json)?\n(.*?)```", raw, re.S):
        candidates.append(match.group(1).strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _extract_expert_payload(raw: str) -> tuple[str, str, Dict[str, str]] | None:
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

    task = payload.get("task") or payload.get("analysis_task") or "执行专家委员会分析"
    context = payload.get("context") or payload.get("news_pack") or payload.get("input") or ""
    return task, context, normalized_outputs


class ExpertCouncilRunner:
    """
    专家委员会执行器
    
    封装专家评审与裁决流程的执行逻辑（独立分析由外部提供）。
    """
    
    def __init__(self, config: AppConfig):
        """初始化执行器"""
        self.config = config
        
        # 创建各专家的模型实例
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
        expert_outputs: Dict[str, str],
    ) -> str:
        """执行专家委员会流程（阶段1输出由外部提供）"""
        if not expert_outputs:
            return "未提供专家输出，无法进行交叉评审。"

        report_parts = []
        report_parts.append("# 🎭 专家委员会分析报告\n")
        report_parts.append(f"**分析任务**: {task}\n")
        
        # 阶段 1: 独立分析（已提供）
        report_parts.append("\n---\n## 阶段 1: 独立分析（已提供）\n")
        missing_experts = [
            expert for expert in _EXPECTED_EXPERTS if expert not in expert_outputs
        ]
        if missing_experts:
            report_parts.append(f"⚠️ 缺少专家输出: {', '.join(missing_experts)}\n")

        for expert in _EXPECTED_EXPERTS:
            if expert not in expert_outputs:
                continue
            output = expert_outputs[expert]
            preview = output[:500] + "..." if len(output) > 500 else output
            report_parts.append(f"\n### {expert}\n{preview}\n")
        
        # 阶段 2: 交叉评审
        report_parts.append("\n---\n## 阶段 2: 交叉评审\n")
        reviews, grade_summary = await self._stage2_cross_review(expert_outputs, context)
        
        report_parts.append("\n### 评审等级汇总\n")
        for reviewee, grades in grade_summary.items():
            avg_grade = self._calculate_average_grade(grades)
            report_parts.append(f"- **{reviewee}**: {avg_grade} (来自 {len(grades)} 位评审)\n")
        
        # 识别分歧
        conflicts = self._identify_conflicts(reviews)
        
        # 阶段 3: 共识讨论
        discussion_results = ""
        if conflicts:
            report_parts.append(f"\n---\n## 阶段 3: 共识讨论\n")
            report_parts.append(f"发现 {len(conflicts)} 个需要讨论的分歧点\n")
            discussion_results = await self._stage3_consensus_discussion(
                conflicts, expert_outputs, context
            )
            report_parts.append(discussion_results)
        else:
            report_parts.append("\n---\n## 阶段 3: 共识讨论\n")
            report_parts.append("✅ 专家意见基本一致，无需额外讨论\n")
        
        # 阶段 4: 主管综合裁决
        report_parts.append("\n---\n## 阶段 4: 主管综合裁决\n")
        final_synthesis = await self._stage4_chairman_synthesis(
            task, expert_outputs, reviews, grade_summary, conflicts, discussion_results
        )
        report_parts.append(final_synthesis)
        
        return "\n".join(report_parts)
    
    async def _stage2_cross_review(
        self, expert_outputs: Dict[str, str], context: str
    ) -> tuple[List[Dict], Dict[str, List[str]]]:
        """阶段2: 交叉评审"""
        reviews = []
        grade_summary: Dict[str, List[str]] = {}
        
        async def do_review(reviewer: str, reviewee: str, focus: str) -> Dict:
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
                {"role": "user", "content": prompt}
            ]
            
            try:
                response = await model.ainvoke(messages)
                grade = self._extract_grade(response.content)
                return {
                    "reviewer": reviewer,
                    "reviewee": reviewee,
                    "grade": grade,
                    "content": response.content,
                }
            except Exception as e:
                return {
                    "reviewer": reviewer,
                    "reviewee": reviewee,
                    "grade": "C",
                    "content": f"评审失败: {str(e)}",
                }
        
        # 收集所有评审任务
        review_tasks = []
        for reviewee, reviewer_configs in CROSS_REVIEW_MATRIX.items():
            if reviewee not in expert_outputs:
                continue
            for config in reviewer_configs:
                reviewer = config["reviewer"]
                if reviewer in expert_outputs:
                    review_tasks.append(
                        do_review(reviewer, reviewee, config["focus"])
                    )
        
        # 并行执行
        results = await asyncio.gather(*review_tasks)
        
        for result in results:
            reviews.append(result)
            reviewee = result["reviewee"]
            if reviewee not in grade_summary:
                grade_summary[reviewee] = []
            grade_summary[reviewee].append(result["grade"])
        
        return reviews, grade_summary
    
    def _identify_conflicts(self, reviews: List[Dict]) -> List[Dict]:
        """识别需要讨论的分歧点"""
        conflicts = []
        for review in reviews:
            grade = review.get("grade", "B")
            if grade in ("C", "D"):
                conflicts.append({
                    "topic": f"{review['reviewer']} 对 {review['reviewee']} 的评审",
                    "grade": grade,
                    "reviewer": review["reviewer"],
                    "reviewee": review["reviewee"],
                    "content": review.get("content", "")[:300],
                })
        return conflicts
    
    async def _stage3_consensus_discussion(
        self,
        conflicts: List[Dict],
        expert_outputs: Dict[str, str],
        context: str,
    ) -> str:
        """阶段3: 共识讨论"""
        if not conflicts:
            return "无需讨论"
        
        discussions = []
        for conflict in conflicts[:3]:  # 最多讨论 3 个分歧
            reviewer = conflict["reviewer"]
            reviewee = conflict["reviewee"]
            
            model = self.expert_models.get(reviewee)
            if not model:
                continue
            
            prompt = f"""你是 {reviewee}，你的分析被 {reviewer} 评为 {conflict['grade']} 级。

{reviewer} 的评审意见:
{conflict['content']}

请针对这些意见进行回应（200字内）。
"""
            
            try:
                messages = [{"role": "user", "content": prompt}]
                response = await model.ainvoke(messages)
                discussions.append(f"\n### 分歧: {conflict['topic']}\n")
                discussions.append(f"**评审等级**: {conflict['grade']}\n")
                discussions.append(f"**{reviewee} 的回应**:\n{response.content}\n")
            except Exception as e:
                discussions.append(f"\n### 分歧: {conflict['topic']}\n")
                discussions.append(f"讨论失败: {str(e)}\n")
        
        return "\n".join(discussions)
    
    async def _stage4_chairman_synthesis(
        self,
        task: str,
        expert_outputs: Dict[str, str],
        reviews: List[Dict],
        grade_summary: Dict[str, List[str]],
        conflicts: List[Dict],
        discussion_results: str,
    ) -> str:
        """阶段4: 主管综合裁决"""
        model = self.expert_models["expert_supervisor"]
        
        # 格式化输入
        expert_text = "\n\n".join([
            f"### {name}\n{output[:800]}..." if len(output) > 800 else f"### {name}\n{output}"
            for name, output in expert_outputs.items()
        ])
        
        review_text = "\n".join([
            f"- {reviewee}: 平均等级 {self._calculate_average_grade(grades)}"
            for reviewee, grades in grade_summary.items()
        ])
        
        conflict_text = "\n".join([
            f"- {c['topic']}: 等级 {c['grade']}"
            for c in conflicts
        ]) if conflicts else "无明显分歧"
        
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
{discussion_results if discussion_results else "专家意见一致，未进行讨论"}

---

请生成最终的综合裁决报告，使用 Markdown 格式。
"""
        
        try:
            messages = [
                {"role": "system", "content": _EXPERT_PROMPTS["expert_supervisor"]},
                {"role": "user", "content": prompt}
            ]
            response = await model.ainvoke(messages)
            return response.content
        except Exception as e:
            return f"主管综合失败: {str(e)}"
    
    def _extract_grade(self, text: str) -> str:
        """从文本中提取评审等级"""
        import re
        
        try:
            json_match = re.search(r'"overall_grade"\s*:\s*"([ABCD])"', text, re.IGNORECASE)
            if json_match:
                return json_match.group(1).upper()
        except Exception:
            pass
        
        grade_match = re.search(r'等级[：:]\s*([ABCD])', text, re.IGNORECASE)
        if grade_match:
            return grade_match.group(1).upper()
        
        return "B"
    
    def _calculate_average_grade(self, grades: List[str]) -> str:
        """计算平均等级"""
        if not grades:
            return "B"
        
        grade_values = {"A": 4, "B": 3, "C": 2, "D": 1}
        avg = sum(grade_values.get(g, 3) for g in grades) / len(grades)
        
        if avg >= 3.5:
            return "A"
        elif avg >= 2.5:
            return "B"
        elif avg >= 1.5:
            return "C"
        else:
            return "D"


def create_council(config: AppConfig) -> CompiledSubAgent:
    """
    创建专家委员会 SubAgent
    
    Args:
        config: 应用配置
        
    Returns:
        配置好的 CompiledSubAgent
    """
    runner = ExpertCouncilRunner(config)
    
    def invoke_fn(state: dict, config_: RunnableConfig | None = None) -> dict:
        """同步调用"""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": [AIMessage(content="未提供分析任务")]}
        
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

        if not expert_outputs:
            last_message = messages[-1]
            task_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            payload = _extract_expert_payload(task_content)
            if not payload:
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

            task, context, expert_outputs = payload
        
        try:
            result = asyncio.run(runner.run_council(
                task=task,
                context=context,
                expert_outputs=expert_outputs,
            ))
        except Exception as e:
            result = f"专家委员会执行失败: {str(e)}"
        
        return {
            "messages": [
                *messages,
                AIMessage(content=result)
            ]
        }
    
    async def ainvoke_fn(state: dict, config_: RunnableConfig | None = None) -> dict:
        """异步调用"""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": [AIMessage(content="未提供分析任务")]}
        
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

        if not expert_outputs:
            last_message = messages[-1]
            task_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            payload = _extract_expert_payload(task_content)
            if not payload:
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

            task, context, expert_outputs = payload
        
        try:
            result = await runner.run_council(
                task=task,
                context=context,
                expert_outputs=expert_outputs,
            )
        except Exception as e:
            result = f"专家委员会执行失败: {str(e)}"
        
        return {
            "messages": [
                *messages,
                AIMessage(content=result)
            ]
        }
    
    runnable = RunnableLambda(invoke_fn, afunc=ainvoke_fn)
    
    return CompiledSubAgent(
        name="expert_council",
        description=(
            "基于已有专家输出执行交叉评审→共识讨论→主管综合。"
            "调用前需提供 summarizer/fact_checker/researcher/impact_assessor 输出。"
        ),
        runnable=runnable,
    )


__all__ = ["create_council", "ExpertCouncilRunner"]
