"""LangChain 回调处理器，用于显示 Agent 执行过程"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from .logger import logger


class AgentProgressCallback(BaseCallbackHandler):
    """
    Agent 执行进度回调处理器。
    
    显示 LLM 调用、工具调用、Agent 执行等关键步骤的日志。
    """
    
    def __init__(self, verbose: bool = True):
        """
        初始化回调处理器。
        
        Args:
            verbose: 是否显示详细日志
        """
        super().__init__()
        self.verbose = verbose
        self._step_count = 0
        self._current_agent = "master"
    
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
        """LLM 开始调用时触发"""
        self._step_count += 1
        # 安全获取模型名称
        model_name = "unknown"
        if serialized:
            model_name = serialized.get("kwargs", {}).get("model_name") or \
                         serialized.get("kwargs", {}).get("model") or \
                         serialized.get("name", "unknown")
        logger.info(f"🤖 [步骤 {self._step_count}] 正在调用 LLM: {model_name}")
        if self.verbose and prompts:
            # 只显示前 200 字符
            prompt_preview = prompts[0][:200] + "..." if len(prompts[0]) > 200 else prompts[0]
            logger.debug(f"   提示词预览: {prompt_preview}")
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 调用完成时触发"""
        logger.info(f"✅ [步骤 {self._step_count}] LLM 调用完成")
        if self.verbose and response.generations:
            # 显示生成的内容预览
            for gen in response.generations[0]:
                content = gen.text[:300] + "..." if len(gen.text) > 300 else gen.text
                logger.debug(f"   响应预览: {content}")
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 调用出错时触发"""
        logger.error(f"❌ [步骤 {self._step_count}] LLM 错误: {error}")
    
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
        """Chain 开始执行时触发"""
        if not serialized:
            return  # 跳过空的 serialized
        chain_name = serialized.get("name") or "unknown"
        if isinstance(serialized.get("id"), list) and serialized["id"]:
            chain_name = chain_name or serialized["id"][-1]
        if chain_name and chain_name not in ("RunnableSequence", "unknown"):
            logger.info(f"🔗 开始执行链: {chain_name}")
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Chain 执行完成时触发"""
        pass  # 避免太多日志
    
    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Chain 执行出错时触发"""
        logger.error(f"❌ Chain 错误: {error}")
    
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
        """工具开始调用时触发"""
        tool_name = serialized.get("name", "unknown") if serialized else "unknown"
        logger.info(f"🔧 正在调用工具: {tool_name}")
        if self.verbose and input_str:
            input_preview = input_str[:200] + "..." if len(input_str) > 200 else input_str
            logger.debug(f"   工具输入: {input_preview}")
    
    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """工具调用完成时触发"""
        logger.info(f"✅ 工具调用完成")
        if self.verbose:
            output_preview = str(output)[:300] + "..." if len(str(output)) > 300 else str(output)
            logger.debug(f"   工具输出: {output_preview}")
    
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """工具调用出错时触发"""
        logger.error(f"❌ 工具错误: {error}")
    
    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Agent 执行动作时触发"""
        tool_name = getattr(action, "tool", "unknown")
        logger.info(f"🎯 Agent 决定调用: {tool_name}")
    
    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Agent 完成时触发"""
        logger.info(f"🏁 Agent 执行完成")


class StreamingProgressCallback(BaseCallbackHandler):
    """
    流式输出回调处理器。
    
    实时显示 LLM 生成的 token。
    """
    
    def __init__(self, print_tokens: bool = True):
        super().__init__()
        self.print_tokens = print_tokens
        self._buffer = ""
    
    def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """每个新 token 生成时触发"""
        if self.print_tokens:
            print(token, end="", flush=True)
            self._buffer += token
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """LLM 完成时换行"""
        if self.print_tokens and self._buffer:
            print()  # 换行
            self._buffer = ""


def get_default_callbacks(verbose: bool = False, streaming: bool = False) -> List[BaseCallbackHandler]:
    """
    获取默认的回调处理器列表。
    
    Args:
        verbose: 是否显示详细日志
        streaming: 是否启用流式输出
        
    Returns:
        回调处理器列表
    """
    callbacks = [AgentProgressCallback(verbose=verbose)]
    if streaming:
        callbacks.append(StreamingProgressCallback())
    return callbacks


__all__ = [
    "AgentProgressCallback",
    "StreamingProgressCallback", 
    "get_default_callbacks",
]

