"""SubAgent 基础工具

提供创建 SubAgent 的通用工具函数。
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda


def create_structured_runnable(
    model: Any,
    output_schema: type,
    system_prompt: str,
) -> RunnableLambda:
    """
    创建一个带结构化输出的 Runnable。
    
    使用 model.with_structured_output() 确保输出符合 Pydantic schema。
    
    Args:
        model: LangChain 聊天模型
        output_schema: Pydantic 模型类
        system_prompt: 系统提示词
    
    Returns:
        可调用的 Runnable
    """
    structured_model = model.with_structured_output(output_schema)
    
    def invoke_fn(state: dict, config: RunnableConfig | None = None) -> dict:
        messages = state.get("messages", [])
        
        # 构建消息列表
        full_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if isinstance(msg, HumanMessage):
                full_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                full_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                full_messages.append(msg)
        
        # 调用模型获取结构化输出
        result = structured_model.invoke(full_messages, config=config)
        
        # 将 Pydantic 对象转为 JSON 字符串返回
        if hasattr(result, "model_dump_json"):
            result_str = result.model_dump_json(indent=2)
        else:
            result_str = str(result)
        
        return {
            "messages": [
                *messages,
                AIMessage(content=result_str)
            ]
        }
    
    return RunnableLambda(invoke_fn)


__all__ = ["create_structured_runnable"]

