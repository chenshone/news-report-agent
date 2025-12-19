"""Agent 执行追踪和可视化

提供完整的 Agent 执行历史记录、实时终端可视化和 HTML 报告生成。
替代 LangSmith 的免费可视化方案。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box


# ============================================================================
# 事件类型定义
# ============================================================================

class EventType(str, Enum):
    """Agent 事件类型"""
    # Agent 级别
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"
    
    # LLM 调用
    LLM_START = "llm_start"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"
    LLM_TOKEN = "llm_token"
    
    # 工具调用
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    
    # 子 Agent 调用
    SUBAGENT_START = "subagent_start"
    SUBAGENT_END = "subagent_end"
    SUBAGENT_ERROR = "subagent_error"
    
    # Chain 执行
    CHAIN_START = "chain_start"
    CHAIN_END = "chain_end"
    CHAIN_ERROR = "chain_error"
    
    # 反思和规划
    REFLECTION = "reflection"
    PLANNING = "planning"
    
    # 自定义事件
    CUSTOM = "custom"


@dataclass
class AgentEvent:
    """Agent 执行事件"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    type: EventType = EventType.CUSTOM
    name: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: Optional[float] = None
    
    # 输入输出
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 错误信息
    error: Optional[str] = None
    
    # 层级关系
    parent_id: Optional[str] = None
    depth: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "timestamp": self.timestamp,
            "timestamp_formatted": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S.%f")[:-3],
            "duration_ms": self.duration_ms,
            "input_preview": self._preview(self.input_data, 200),
            "output_preview": self._preview(self.output_data, 300),
            "input_full": self._to_json_safe(self.input_data),
            "output_full": self._to_json_safe(self.output_data),
            "metadata": self.metadata,
            "error": self.error,
            "parent_id": self.parent_id,
            "depth": self.depth,
        }
    
    def _preview(self, data: Any, max_len: int = 200) -> Optional[str]:
        """生成预览文本"""
        if data is None:
            return None
        text = str(data)
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text
    
    def _to_json_safe(self, data: Any) -> Any:
        """转换为 JSON 安全格式"""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, (list, tuple)):
            return [self._to_json_safe(item) for item in data]
        if isinstance(data, dict):
            return {k: self._to_json_safe(v) for k, v in data.items()}
        return str(data)


# ============================================================================
# Agent 追踪器
# ============================================================================

class AgentTracer:
    """
    Agent 执行追踪器。
    
    记录完整的执行历史，支持：
    - 事件层级结构
    - 时间统计
    - 导出为 JSON/HTML
    """
    
    def __init__(self, session_name: Optional[str] = None):
        self.session_id = str(uuid4())[:8]
        self.session_name = session_name or f"session-{self.session_id}"
        self.start_time = time.time()
        self.events: List[AgentEvent] = []
        
        # 用于跟踪正在进行的事件
        self._active_events: Dict[str, AgentEvent] = {}
        self._event_stack: List[str] = []  # 维护父子关系
        
        # 统计信息
        self.stats = {
            "llm_calls": 0,
            "tool_calls": 0,
            "subagent_calls": 0,
            "total_tokens": 0,
            "errors": 0,
        }
    
    @property
    def current_parent_id(self) -> Optional[str]:
        """获取当前父事件 ID"""
        return self._event_stack[-1] if self._event_stack else None
    
    @property
    def current_depth(self) -> int:
        """获取当前深度"""
        return len(self._event_stack)
    
    def start_event(
        self,
        event_type: EventType,
        name: str,
        input_data: Any = None,
        metadata: Optional[Dict] = None,
    ) -> AgentEvent:
        """开始一个事件"""
        event = AgentEvent(
            type=event_type,
            name=name,
            input_data=input_data,
            metadata=metadata or {},
            parent_id=self.current_parent_id,
            depth=self.current_depth,
        )
        
        self.events.append(event)
        self._active_events[event.id] = event
        self._event_stack.append(event.id)
        
        # 更新统计
        if event_type == EventType.LLM_START:
            self.stats["llm_calls"] += 1
        elif event_type == EventType.TOOL_START:
            self.stats["tool_calls"] += 1
        elif event_type == EventType.SUBAGENT_START:
            self.stats["subagent_calls"] += 1
        
        return event
    
    def end_event(
        self,
        event_id: str,
        output_data: Any = None,
        error: Optional[str] = None,
    ) -> Optional[AgentEvent]:
        """结束一个事件"""
        if event_id not in self._active_events:
            return None
        
        event = self._active_events.pop(event_id)
        event.output_data = output_data
        event.error = error
        event.duration_ms = (time.time() - event.timestamp) * 1000
        
        if error:
            self.stats["errors"] += 1
        
        # 从栈中移除
        if self._event_stack and self._event_stack[-1] == event_id:
            self._event_stack.pop()
        
        return event
    
    def add_event(
        self,
        event_type: EventType,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> AgentEvent:
        """添加一个完整的事件（非嵌套）"""
        event = AgentEvent(
            type=event_type,
            name=name,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata or {},
            duration_ms=duration_ms,
            error=error,
            parent_id=self.current_parent_id,
            depth=self.current_depth,
        )
        self.events.append(event)
        
        if error:
            self.stats["errors"] += 1
            
        return event
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        total_duration = time.time() - self.start_time
        
        # 计算各类型耗时
        llm_time = sum(
            e.duration_ms or 0 
            for e in self.events 
            if e.type in (EventType.LLM_START, EventType.LLM_END)
        )
        tool_time = sum(
            e.duration_ms or 0 
            for e in self.events 
            if e.type in (EventType.TOOL_START, EventType.TOOL_END)
        )
        
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "total_duration_s": round(total_duration, 2),
            "total_events": len(self.events),
            "llm_calls": self.stats["llm_calls"],
            "tool_calls": self.stats["tool_calls"],
            "subagent_calls": self.stats["subagent_calls"],
            "errors": self.stats["errors"],
            "llm_time_ms": round(llm_time, 2),
            "tool_time_ms": round(tool_time, 2),
        }
    
    def export_json(self, path: Optional[str] = None) -> str:
        """导出为 JSON"""
        data = {
            "summary": self.get_summary(),
            "events": [e.to_dict() for e in self.events],
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        if path:
            Path(path).write_text(json_str, encoding="utf-8")
        
        return json_str
    
    def export_html(self, path: Optional[str] = None) -> str:
        """导出为交互式 HTML 报告"""
        html = generate_html_report(self)
        
        if path:
            Path(path).write_text(html, encoding="utf-8")
        
        return html
    
    def build_tree(self) -> Dict[str, Any]:
        """构建事件树结构"""
        events_by_id = {e.id: e.to_dict() for e in self.events}
        root_events = []
        
        for event in self.events:
            event_dict = events_by_id[event.id]
            event_dict["children"] = []
            
            if event.parent_id and event.parent_id in events_by_id:
                parent = events_by_id[event.parent_id]
                if "children" not in parent:
                    parent["children"] = []
                parent["children"].append(event_dict)
            else:
                root_events.append(event_dict)
        
        return {"events": root_events}


# ============================================================================
# Rich 终端可视化回调
# ============================================================================

class RichAgentCallback(BaseCallbackHandler):
    """
    Rich 终端可视化回调处理器。
    
    实时显示 Agent 执行过程，包括：
    - 树形结构展示调用链
    - 工具调用详情
    - LLM 思考过程
    - 错误高亮
    """
    
    def __init__(
        self,
        tracer: Optional[AgentTracer] = None,
        show_input: bool = True,
        show_output: bool = True,
        console: Optional[Console] = None,
    ):
        super().__init__()
        self.tracer = tracer or AgentTracer()
        self.show_input = show_input
        self.show_output = show_output
        self.console = console or Console()
        
        # 运行时状态
        self._run_id_to_event: Dict[str, str] = {}
        self._step_count = 0
        self._current_tree: Optional[Tree] = None
        
        # 显示配置
        self.icons = {
            EventType.LLM_START: "🤖",
            EventType.TOOL_START: "🔧",
            EventType.SUBAGENT_START: "👤",
            EventType.CHAIN_START: "🔗",
            EventType.REFLECTION: "💭",
            EventType.PLANNING: "📋",
            EventType.AGENT_ERROR: "❌",
        }
    
    def _get_icon(self, event_type: EventType) -> str:
        """获取事件类型对应的图标"""
        return self.icons.get(event_type, "▶")
    
    def _print_event_start(self, event_type: EventType, name: str, detail: str = ""):
        """打印事件开始"""
        self._step_count += 1
        icon = self._get_icon(event_type)
        depth = self.tracer.current_depth
        indent = "  " * depth
        
        # 构建显示文本
        step_text = Text()
        step_text.append(f"{indent}{icon} ", style="bold")
        step_text.append(f"[步骤 {self._step_count}] ", style="dim")
        step_text.append(name, style="bold cyan")
        
        if detail:
            step_text.append(f"\n{indent}   ", style="")
            step_text.append(detail[:150] + ("..." if len(detail) > 150 else ""), style="dim")
        
        self.console.print(step_text)
    
    def _print_event_end(self, event_type: EventType, name: str, output: str = "", error: str = "", duration_ms: float = 0):
        """打印事件结束"""
        depth = self.tracer.current_depth
        indent = "  " * depth
        
        if error:
            self.console.print(f"{indent}❌ [bold red]{name} 失败:[/] {error[:100]}")
        else:
            duration_text = f"({duration_ms:.0f}ms)" if duration_ms else ""
            self.console.print(f"{indent}✅ [green]{name}[/] 完成 [dim]{duration_text}[/]")
            
            if output and self.show_output:
                output_preview = output[:200] + ("..." if len(output) > 200 else "")
                self.console.print(f"{indent}   [dim]→ {output_preview}[/]")
    
    # LangChain Callback 方法
    
    # 子 Agent 识别配置
    # 使用更精确的模式：必须以 "你是" 开头的角色定义
    SUBAGENT_PATTERNS = {
        "query_planner": ["你是查询规划专家"],
        "summarizer": ["你是摘要专家"],
        "fact_checker": ["你是事实核查专家"],
        "researcher": ["你是背景研究专家"],
        "impact_assessor": ["你是影响评估专家"],
        "expert_supervisor": ["你是专家主管"],
    }
    
    # Master Agent 的标识特征（用于排除误判）
    MASTER_AGENT_MARKERS = [
        "热点资讯分析智能体",
        "热点资讯聚合",
        "# 角色定义",
    ]
    
    def _detect_subagent(self, prompt: str) -> Optional[str]:
        """检测 prompt 是否来自子 Agent，返回子 Agent 名称"""
        # 首先排除 Master Agent
        for marker in self.MASTER_AGENT_MARKERS:
            if marker in prompt:
                return None
        
        # 检测子 Agent - 使用精确的角色定义模式
        for agent_name, patterns in self.SUBAGENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in prompt:
                    return agent_name
        return None
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 开始调用"""
        model_name = "LLM"
        if serialized:
            model_name = serialized.get("kwargs", {}).get("model_name") or \
                        serialized.get("kwargs", {}).get("model") or \
                        serialized.get("name", "LLM")
        
        # 检测是否是子 Agent 调用
        subagent_name = None
        if prompts:
            subagent_name = self._detect_subagent(prompts[0])
        
        if subagent_name:
            # 子 Agent 调用
            event_type = EventType.SUBAGENT_START
            event_name = f"👤 {subagent_name}"
            # 注意：统计在 start_event 中自动更新
        else:
            # 普通 LLM 调用
            event_type = EventType.LLM_START
            event_name = f"调用 {model_name}"
        
        event = self.tracer.start_event(
            event_type,
            event_name,
            input_data=prompts[0] if prompts else None,  # 保存完整 prompt
            metadata={"model": model_name, "tags": tags or [], "subagent": subagent_name},
        )
        self._run_id_to_event[str(run_id)] = event.id
        
        prompt_preview = prompts[0][:100] + "..." if prompts and len(prompts[0]) > 100 else (prompts[0] if prompts else "")
        self._print_event_start(event_type, event_name, prompt_preview)
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 调用完成"""
        event_id = self._run_id_to_event.get(str(run_id))
        if not event_id:
            return
        
        # 尝试多种方式获取输出和决策信息
        output: str = ""
        tool_calls: List[Dict] = []
        
        try:
            if response.generations and response.generations[0]:
                gen = response.generations[0][0]
                
                # 尝试获取 text 属性
                if hasattr(gen, 'text') and gen.text:
                    output = str(gen.text)
                
                # 尝试获取 message（ChatModel 返回格式）
                if hasattr(gen, 'message'):
                    msg = getattr(gen, 'message', None)
                    if msg:
                        # 获取内容
                        if hasattr(msg, 'content') and msg.content:
                            output = str(msg.content)
                        
                        # 🎯 捕获工具调用决策
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_calls.append({
                                    "name": tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown"),
                                    "args": tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {}),
                                })
                        
                        # 检查 additional_kwargs 中的 function_call
                        if hasattr(msg, 'additional_kwargs'):
                            ak = msg.additional_kwargs
                            if ak.get('function_call'):
                                fc = ak['function_call']
                                tool_calls.append({
                                    "name": fc.get("name", "unknown"),
                                    "args": fc.get("arguments", ""),
                                })
                            if ak.get('tool_calls'):
                                for tc in ak['tool_calls']:
                                    func = tc.get('function', {})
                                    tool_calls.append({
                                        "name": func.get("name", "unknown"),
                                        "args": func.get("arguments", ""),
                                    })
                
                # 尝试直接转字符串
                if not output and gen:
                    output = str(gen)
                    
        except Exception as e:
            output = f"[获取输出失败: {e}]"
        
        # 如果检测到工具调用决策，添加决策事件
        if tool_calls:
            for tc in tool_calls:
                self.tracer.add_event(
                    EventType.PLANNING,
                    f"🎯 决策: 调用 {tc['name']}",
                    input_data={"reasoning": output[:500] if output else None},
                    output_data={"tool": tc["name"], "args": tc["args"]},
                )
                self.console.print(f"  🎯 [bold yellow]决策: 调用 {tc['name']}[/]")
                if tc["args"]:
                    args_str = str(tc["args"])[:100]
                    self.console.print(f"     [dim]参数: {args_str}[/]")
        
        # 构建完整输出（包含决策信息）
        full_output = output
        if tool_calls:
            tool_info = "\n\n📌 工具调用决策:\n" + "\n".join(
                f"  - {tc['name']}: {tc['args']}" for tc in tool_calls
            )
            full_output = output + tool_info if output else tool_info
        
        event = self.tracer.end_event(event_id, output_data=full_output)
        duration = (event.duration_ms or 0) if event else 0
        
        # 根据原始事件类型确定显示名称
        if event and event.type == EventType.SUBAGENT_START:
            subagent_name = event.metadata.get("subagent", "子Agent")
            self._print_event_end(EventType.SUBAGENT_END, f"👤 {subagent_name}", str(output), duration_ms=duration)
        else:
            self._print_event_end(EventType.LLM_END, "LLM", str(output), duration_ms=duration)
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 调用出错"""
        event_id = self._run_id_to_event.get(str(run_id))
        if event_id:
            self.tracer.end_event(event_id, error=str(error))
        
        self._print_event_end(EventType.LLM_ERROR, "LLM", error=str(error))
    
    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """工具开始调用"""
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        
        event = self.tracer.start_event(
            EventType.TOOL_START,
            f"工具: {tool_name}",
            input_data=input_str,
            metadata={"tool": tool_name},
        )
        self._run_id_to_event[str(run_id)] = event.id
        
        self._print_event_start(EventType.TOOL_START, f"工具: {tool_name}", input_str if self.show_input else "")
    
    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """工具调用完成"""
        event_id = self._run_id_to_event.get(str(run_id))
        if not event_id:
            return
        
        event = self.tracer.end_event(event_id, output_data=str(output))
        duration = (event.duration_ms or 0) if event else 0
        
        self._print_event_end(EventType.TOOL_END, "工具", str(output), duration_ms=duration)
    
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """工具调用出错"""
        event_id = self._run_id_to_event.get(str(run_id))
        if event_id:
            self.tracer.end_event(event_id, error=str(error))
        
        self._print_event_end(EventType.TOOL_ERROR, "工具", error=str(error))
    
    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Chain 开始执行"""
        if not serialized:
            return
        
        chain_name = serialized.get("name") or "Chain"
        if chain_name in ("RunnableSequence", "unknown"):
            return
        
        # 检测子 Agent 调用
        is_subagent = "task" in chain_name.lower() or any(
            keyword in chain_name.lower() 
            for keyword in ["query_planner", "summarizer", "fact_checker", "researcher", "impact_assessor", "supervisor"]
        )
        
        event_type = EventType.SUBAGENT_START if is_subagent else EventType.CHAIN_START
        
        event = self.tracer.start_event(
            event_type,
            chain_name,
            input_data=inputs,
            metadata={"tags": tags or []},
        )
        self._run_id_to_event[str(run_id)] = event.id
        
        self._print_event_start(event_type, chain_name)
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Chain 执行完成"""
        event_id = self._run_id_to_event.get(str(run_id))
        if not event_id:
            return
        
        event = self.tracer.end_event(event_id, output_data=outputs)
        if event:
            duration = event.duration_ms or 0
            self._print_event_end(EventType.CHAIN_END, event.name, duration_ms=duration)
    
    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Chain 执行出错"""
        event_id = self._run_id_to_event.get(str(run_id))
        if event_id:
            self.tracer.end_event(event_id, error=str(error))
        
        self._print_event_end(EventType.CHAIN_ERROR, "Chain", error=str(error))
    
    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Agent 执行动作 - 捕获决策过程"""
        tool_name = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")
        
        # 尝试获取 Agent 的思考过程
        log = getattr(action, "log", "")
        message_log = getattr(action, "message_log", [])
        
        # 构建决策详情
        decision_detail = {
            "tool": tool_name,
            "tool_input": tool_input,
            "reasoning": log if log else None,
        }
        
        # 如果有 message_log，提取最后一条消息的内容作为思考
        if message_log and not log:
            try:
                last_msg = message_log[-1] if message_log else None
                if last_msg and hasattr(last_msg, 'content'):
                    decision_detail["reasoning"] = str(last_msg.content)
            except Exception:
                pass
        
        self.tracer.add_event(
            EventType.PLANNING,
            f"🎯 决策: 调用 {tool_name}",
            input_data=decision_detail,
            output_data=f"参数: {tool_input}" if tool_input else None,
        )
        
        # 美化终端输出
        depth = self.tracer.current_depth
        indent = "  " * depth
        self.console.print(f"{indent}🎯 [bold yellow]Agent 决策[/]")
        if log:
            # 显示思考过程
            reasoning_preview = log[:200] + "..." if len(log) > 200 else log
            self.console.print(f"{indent}   [dim]💭 思考: {reasoning_preview}[/]")
        self.console.print(f"{indent}   [cyan]→ 决定调用: {tool_name}[/]")
        if tool_input:
            input_preview = str(tool_input)[:100] + "..." if len(str(tool_input)) > 100 else str(tool_input)
            self.console.print(f"{indent}   [dim]📥 参数: {input_preview}[/]")
    
    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Agent 完成 - 捕获最终输出"""
        output = getattr(finish, "return_values", {})
        log = getattr(finish, "log", "")
        
        self.tracer.add_event(
            EventType.AGENT_END,
            "🏁 Agent 执行完成",
            input_data=log if log else None,
            output_data=output,
        )
        
        depth = self.tracer.current_depth
        indent = "  " * depth
        self.console.print(f"{indent}🏁 [bold green]Agent 执行完成[/]")
        if log:
            log_preview = log[:150] + "..." if len(log) > 150 else log
            self.console.print(f"{indent}   [dim]{log_preview}[/]")
    
    def print_summary(self):
        """打印执行摘要"""
        summary = self.tracer.get_summary()
        
        table = Table(title="执行摘要", box=box.ROUNDED)
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green")
        
        table.add_row("会话 ID", summary["session_id"])
        table.add_row("总耗时", f"{summary['total_duration_s']:.2f} 秒")
        table.add_row("总事件数", str(summary["total_events"]))
        table.add_row("LLM 调用次数", str(summary["llm_calls"]))
        table.add_row("工具调用次数", str(summary["tool_calls"]))
        table.add_row("子 Agent 调用", str(summary["subagent_calls"]))
        table.add_row("错误数", str(summary["errors"]))
        
        self.console.print("\n")
        self.console.print(table)


# ============================================================================
# HTML 报告生成
# ============================================================================

def generate_html_report(tracer: AgentTracer) -> str:
    """生成交互式 HTML 报告"""
    summary = tracer.get_summary()
    events_json = json.dumps([e.to_dict() for e in tracer.events], ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent 执行追踪报告 - {summary['session_name']}</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
            --border-color: #30363d;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        h1::before {{
            content: "🔍";
        }}
        
        /* 摘要卡片 */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 600;
            color: var(--accent-blue);
        }}
        
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 5px;
        }}
        
        .stat-card.llm .stat-value {{ color: var(--accent-purple); }}
        .stat-card.tool .stat-value {{ color: var(--accent-yellow); }}
        .stat-card.subagent .stat-value {{ color: var(--accent-green); }}
        .stat-card.error .stat-value {{ color: var(--accent-red); }}
        
        /* 时间线 */
        .timeline {{
            position: relative;
            padding-left: 30px;
        }}
        
        .timeline::before {{
            content: "";
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: var(--border-color);
        }}
        
        .event {{
            position: relative;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }}
        
        .event:hover {{
            border-color: var(--accent-blue);
            box-shadow: 0 0 10px rgba(88, 166, 255, 0.1);
        }}
        
        .event::before {{
            content: "";
            position: absolute;
            left: -24px;
            top: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--accent-blue);
            border: 2px solid var(--bg-primary);
        }}
        
        .event.llm_start::before, .event.llm_end::before {{ background: var(--accent-purple); }}
        .event.tool_start::before, .event.tool_end::before {{ background: var(--accent-yellow); }}
        .event.subagent_start::before, .event.subagent_end::before {{ background: var(--accent-green); }}
        .event.agent_error::before, .event.llm_error::before, .event.tool_error::before {{ background: var(--accent-red); }}
        
        .event-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .event-title {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }}
        
        .event-icon {{
            font-size: 18px;
        }}
        
        .event-type {{
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
        }}
        
        .event-meta {{
            display: flex;
            gap: 15px;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .event-content {{
            margin-top: 10px;
        }}
        
        .content-section {{
            margin-top: 10px;
            padding: 10px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            font-family: 'SF Mono', Monaco, 'Consolas', monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        .content-label {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .error-message {{
            color: var(--accent-red);
            background: rgba(248, 81, 73, 0.1);
            border: 1px solid rgba(248, 81, 73, 0.3);
        }}
        
        /* 折叠展开 */
        .event-content.collapsed {{
            display: none;
        }}
        
        .toggle-btn {{
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }}
        
        .toggle-btn:hover {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }}
        
        /* 深度缩进 */
        .depth-1 {{ margin-left: 20px; }}
        .depth-2 {{ margin-left: 40px; }}
        .depth-3 {{ margin-left: 60px; }}
        .depth-4 {{ margin-left: 80px; }}
        
        /* 筛选 */
        .filters {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: white;
        }}
        
        .filter-btn.active.llm {{ background: var(--accent-purple); border-color: var(--accent-purple); }}
        .filter-btn.active.tool {{ background: var(--accent-yellow); border-color: var(--accent-yellow); }}
        .filter-btn.active.subagent {{ background: var(--accent-green); border-color: var(--accent-green); }}
        .filter-btn.active.decision {{ background: #f97316; border-color: #f97316; }}
        
        /* 决策事件特殊样式 */
        .event.planning {{
            border-left: 3px solid #f97316;
            background: linear-gradient(90deg, rgba(249, 115, 22, 0.1) 0%, var(--bg-secondary) 100%);
        }}
        .event.planning::before {{ background: #f97316; }}
        
        /* 决策内容高亮 */
        .decision-box {{
            background: rgba(249, 115, 22, 0.15);
            border: 1px solid rgba(249, 115, 22, 0.3);
            border-radius: 6px;
            padding: 10px;
            margin-top: 8px;
        }}
        .decision-box .tool-name {{
            color: #f97316;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Agent 执行追踪报告</h1>
        
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-value">{summary['total_duration_s']:.1f}s</div>
                <div class="stat-label">总耗时</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['total_events']}</div>
                <div class="stat-label">总事件数</div>
            </div>
            <div class="stat-card llm">
                <div class="stat-value">{summary['llm_calls']}</div>
                <div class="stat-label">LLM 调用</div>
            </div>
            <div class="stat-card tool">
                <div class="stat-value">{summary['tool_calls']}</div>
                <div class="stat-label">工具调用</div>
            </div>
            <div class="stat-card subagent">
                <div class="stat-value">{summary['subagent_calls']}</div>
                <div class="stat-label">子 Agent</div>
            </div>
            <div class="stat-card error">
                <div class="stat-value">{summary['errors']}</div>
                <div class="stat-label">错误</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">全部</button>
            <button class="filter-btn decision" data-filter="decision">🎯 决策</button>
            <button class="filter-btn llm" data-filter="llm">🤖 LLM</button>
            <button class="filter-btn tool" data-filter="tool">🔧 工具</button>
            <button class="filter-btn subagent" data-filter="subagent">👤 子 Agent</button>
            <button class="filter-btn" data-filter="error">❌ 错误</button>
        </div>
        
        <div class="timeline" id="timeline"></div>
    </div>
    
    <script>
        const events = {events_json};
        
        const icons = {{
            'llm_start': '🤖',
            'llm_end': '✅',
            'llm_error': '❌',
            'tool_start': '🔧',
            'tool_end': '✅',
            'tool_error': '❌',
            'subagent_start': '👤',
            'subagent_end': '✅',
            'chain_start': '🔗',
            'chain_end': '✅',
            'planning': '🎯',
            'reflection': '💭',
            'agent_start': '🚀',
            'agent_end': '🏁',
            'agent_error': '❌',
        }};
        
        function renderEvents(filter = 'all') {{
            const timeline = document.getElementById('timeline');
            timeline.innerHTML = '';
            
            events.forEach((event, index) => {{
                // 筛选
                if (filter !== 'all') {{
                    if (filter === 'llm' && !event.type.includes('llm') && !event.type.includes('subagent')) return;
                    if (filter === 'tool' && !event.type.includes('tool')) return;
                    if (filter === 'subagent' && !event.type.includes('subagent') && !event.type.includes('chain')) return;
                    if (filter === 'decision' && event.type !== 'planning' && event.type !== 'agent_end') return;
                    if (filter === 'error' && !event.type.includes('error') && !event.error) return;
                }}
                
                const div = document.createElement('div');
                div.className = `event ${{event.type}} depth-${{Math.min(event.depth, 4)}}`;
                
                const icon = icons[event.type] || '▶';
                const duration = event.duration_ms ? `${{event.duration_ms.toFixed(0)}}ms` : '';
                
                // 使用完整内容，格式化显示
                const inputContent = formatContent(event.input_full);
                const outputContent = formatContent(event.output_full);
                
                // 决策事件特殊渲染
                const isDecision = event.type === 'planning';
                
                div.innerHTML = `
                    <div class="event-header">
                        <div class="event-title">
                            <span class="event-icon">${{icon}}</span>
                            <span>${{event.name}}</span>
                            <span class="event-type">${{isDecision ? '决策' : event.type}}</span>
                        </div>
                        <button class="toggle-btn" onclick="toggleContent(this)">${{isDecision ? '查看详情' : '展开'}}</button>
                    </div>
                    <div class="event-meta">
                        <span>⏱ ${{event.timestamp_formatted}}</span>
                        ${{duration ? `<span>⏳ ${{duration}}</span>` : ''}}
                    </div>
                    <div class="event-content ${{isDecision ? '' : 'collapsed'}}">
                        ${{isDecision && inputContent ? `
                            <div class="content-label">💭 思考/推理</div>
                            <div class="content-section">${{escapeHtml(inputContent)}}</div>
                        ` : ''}}
                        ${{isDecision && outputContent ? `
                            <div class="content-label">📌 决策结果</div>
                            <div class="decision-box">${{escapeHtml(outputContent)}}</div>
                        ` : ''}}
                        ${{!isDecision && inputContent ? `
                            <div class="content-label">输入</div>
                            <div class="content-section">${{escapeHtml(inputContent)}}</div>
                        ` : ''}}
                        ${{!isDecision && outputContent ? `
                            <div class="content-label">输出</div>
                            <div class="content-section">${{escapeHtml(outputContent)}}</div>
                        ` : ''}}
                        ${{event.error ? `
                            <div class="content-label">错误</div>
                            <div class="content-section error-message">${{escapeHtml(event.error)}}</div>
                        ` : ''}}
                    </div>
                `;
                
                timeline.appendChild(div);
            }});
        }}
        
        function toggleContent(btn) {{
            const content = btn.closest('.event').querySelector('.event-content');
            content.classList.toggle('collapsed');
            btn.textContent = content.classList.contains('collapsed') ? '展开' : '收起';
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function formatContent(data) {{
            // 处理各种数据类型，返回格式化的字符串
            if (data === null || data === undefined) return null;
            if (typeof data === 'string') return data;
            if (typeof data === 'object') {{
                try {{
                    return JSON.stringify(data, null, 2);
                }} catch (e) {{
                    return String(data);
                }}
            }}
            return String(data);
        }}
        
        // 筛选按钮
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderEvents(btn.dataset.filter);
            }});
        }});
        
        // 初始渲染
        renderEvents();
    </script>
</body>
</html>"""
    
    return html


# ============================================================================
# 便捷函数
# ============================================================================

def create_tracing_callback(
    session_name: Optional[str] = None,
    show_input: bool = True,
    show_output: bool = True,
) -> tuple[RichAgentCallback, AgentTracer]:
    """
    创建追踪回调和追踪器。
    
    Args:
        session_name: 会话名称
        show_input: 是否显示输入
        show_output: 是否显示输出
        
    Returns:
        (callback, tracer) 元组
    """
    tracer = AgentTracer(session_name=session_name)
    callback = RichAgentCallback(
        tracer=tracer,
        show_input=show_input,
        show_output=show_output,
    )
    return callback, tracer


__all__ = [
    "EventType",
    "AgentEvent",
    "AgentTracer",
    "RichAgentCallback",
    "generate_html_report",
    "create_tracing_callback",
]

