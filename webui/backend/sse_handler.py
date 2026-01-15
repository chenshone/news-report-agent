"""SSE Callback Handler for Agent Events

Converts LangChain callback events to SSE-compatible format for streaming.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class SSEEventType(str, Enum):
    """SSE event types for frontend display"""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    LLM_START = "llm_start"
    LLM_END = "llm_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_END = "subagent_end"
    ERROR = "error"
    REPORT = "report"


@dataclass
class SSEEvent:
    """SSE event data structure"""
    event_type: SSEEventType
    name: str
    timestamp: float = field(default_factory=time.time)
    detail: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def to_sse_data(self) -> str:
        """Convert to SSE data format"""
        return json.dumps({
            "type": self.event_type.value,
            "name": self.name,
            "timestamp": self.timestamp,
            "time_formatted": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S"),
            "detail": self.detail,
            "error": self.error,
            "data": self.data,
        }, ensure_ascii=False)


class SSECallbackHandler(BaseCallbackHandler):
    """
    Callback handler that pushes events to an asyncio Queue for SSE streaming.
    """
    
    # Subagent detection patterns (from existing tracer.py)
    SUBAGENT_PATTERNS = {
        "query_planner": ["你是查询规划专家"],
        "summarizer": ["你是摘要专家"],
        "fact_checker": ["你是事实核查专家"],
        "researcher": ["你是背景研究专家"],
        "impact_assessor": ["你是影响评估专家"],
        "expert_supervisor": ["你是专家主管"],
    }
    
    MASTER_AGENT_MARKERS = [
        "热点资讯分析智能体",
        "热点资讯聚合",
        "# 角色定义",
    ]
    
    def __init__(self, event_queue: asyncio.Queue):
        super().__init__()
        self.event_queue = event_queue
        self._run_id_to_name: Dict[str, str] = {}
        self._run_id_to_type: Dict[str, SSEEventType] = {}
        
    def _put_event(self, event: SSEEvent):
        """Put event into queue (thread-safe for sync callbacks)"""
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Drop event if queue is full
    
    def _detect_subagent(self, prompt: str) -> Optional[str]:
        """Detect if prompt is from a subagent"""
        for marker in self.MASTER_AGENT_MARKERS:
            if marker in prompt:
                return None
        
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
        **kwargs: Any,
    ) -> Any:
        """LLM call started"""
        model_name = "LLM"
        if serialized:
            model_name = serialized.get("kwargs", {}).get("model_name") or \
                        serialized.get("kwargs", {}).get("model") or \
                        serialized.get("name", "LLM")
        
        # Check if this is a subagent
        subagent_name = None
        if prompts:
            subagent_name = self._detect_subagent(prompts[0])
        
        if subagent_name:
            event_type = SSEEventType.SUBAGENT_START
            name = f"👤 {subagent_name}"
            self._run_id_to_name[str(run_id)] = subagent_name
        else:
            event_type = SSEEventType.LLM_START
            name = f"🤖 {model_name}"
            self._run_id_to_name[str(run_id)] = model_name
        
        self._run_id_to_type[str(run_id)] = event_type
        
        prompt_preview = prompts[0][:100] + "..." if prompts and len(prompts[0]) > 100 else (prompts[0] if prompts else "")
        
        self._put_event(SSEEvent(
            event_type=event_type,
            name=name,
            detail=prompt_preview if event_type == SSEEventType.LLM_START else f"正在执行 {subagent_name} 分析...",
        ))
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM call completed"""
        name = self._run_id_to_name.get(str(run_id), "LLM")
        original_type = self._run_id_to_type.get(str(run_id), SSEEventType.LLM_START)
        
        # Get output preview
        output = ""
        try:
            if response.generations and response.generations[0]:
                gen = response.generations[0][0]
                if hasattr(gen, 'text') and gen.text:
                    output = str(gen.text)[:200]
                elif hasattr(gen, 'message') and hasattr(gen.message, 'content'):
                    output = str(gen.message.content)[:200]
        except Exception:
            output = "[响应已完成]"
        
        end_type = SSEEventType.SUBAGENT_END if original_type == SSEEventType.SUBAGENT_START else SSEEventType.LLM_END
        
        self._put_event(SSEEvent(
            event_type=end_type,
            name=f"✅ {name}",
            detail=output + "..." if len(output) >= 200 else output,
        ))
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> Any:
        """LLM call errored"""
        self._put_event(SSEEvent(
            event_type=SSEEventType.ERROR,
            name="❌ LLM Error",
            error=str(error)[:200],
        ))
    
    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> Any:
        """Tool call started"""
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        self._run_id_to_name[str(run_id)] = tool_name
        
        # Map tool names to friendly Chinese names
        tool_names_cn = {
            "internet_search": "🔍 网络搜索",
            "fetch_page": "📄 获取网页",
            "evaluate_credibility": "✅ 评估可信度",
            "evaluate_relevance": "📊 评估相关性",
        }
        
        display_name = tool_names_cn.get(tool_name, f"🔧 {tool_name}")
        
        self._put_event(SSEEvent(
            event_type=SSEEventType.TOOL_START,
            name=display_name,
            detail=input_str[:150] + "..." if len(input_str) > 150 else input_str,
        ))
    
    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> Any:
        """Tool call completed"""
        tool_name = self._run_id_to_name.get(str(run_id), "工具")
        
        self._put_event(SSEEvent(
            event_type=SSEEventType.TOOL_END,
            name=f"✅ {tool_name}",
            detail=str(output)[:150] + "..." if len(str(output)) > 150 else str(output),
        ))
    
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> Any:
        """Tool call errored"""
        self._put_event(SSEEvent(
            event_type=SSEEventType.ERROR,
            name="❌ Tool Error",
            error=str(error)[:200],
        ))


def create_sse_callback(event_queue: asyncio.Queue) -> SSECallbackHandler:
    """Factory function to create SSE callback handler"""
    return SSECallbackHandler(event_queue)
