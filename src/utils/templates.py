"""报告模板和格式化工具"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_markdown_report(
    query: str,
    result: Dict[str, Any],
    generation_time: Optional[datetime] = None,
) -> str:
    """
    将 Agent 运行结果格式化为 Markdown 报告。
    
    Args:
        query: 用户查询
        result: Agent 运行结果（包含 messages 等）
        generation_time: 生成时间
        
    Returns:
        Markdown 格式的报告
    """
    if generation_time is None:
        generation_time = datetime.now()
    
    # 提取最后一条 AI 消息作为报告内容
    messages = result.get("messages", [])
    report_content = ""
    
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            # 如果是 AIMessage
            if hasattr(msg, "type") and msg.type == "ai":
                report_content = msg.content
                break
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            # 如果是字典格式
            report_content = msg.get("content", "")
            break
    
    # 如果没有找到报告内容，使用默认消息
    if not report_content:
        report_content = "Agent 运行完成，但未生成报告内容。"
    
    # 构建报告
    report_lines = [
        "# 热点资讯分析报告",
        "",
        f"**查询**: {query}",
        f"**生成时间**: {generation_time.strftime('%Y年%m月%d日 %H:%M:%S')}",
        "",
        "---",
        "",
        report_content,
        "",
        "---",
        "",
        f"*本报告由 AI Agent 自动生成于 {generation_time.strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    
    return "\n".join(report_lines)


def format_simple_output(result: Dict[str, Any]) -> str:
    """
    提取 Agent 结果的简单文本输出（用于终端显示）。
    
    Args:
        result: Agent 运行结果
        
    Returns:
        简单的文本输出
    """
    messages = result.get("messages", [])
    
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            return msg.get("content", "")
    
    return "Agent 运行完成，但未生成输出内容。"


def extract_tool_calls(result: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    提取 Agent 运行过程中的工具调用记录。
    
    Args:
        result: Agent 运行结果
        
    Returns:
        工具调用列表，每项包含 tool_name 和 args
    """
    tool_calls = []
    messages = result.get("messages", [])
    
    for msg in messages:
        # 检查是否有 tool_calls 属性
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls.append({
                    "tool_name": tool_call.get("name", "unknown"),
                    "args": str(tool_call.get("args", {})),
                })
        # 检查字典格式
        elif isinstance(msg, dict) and "tool_calls" in msg:
            for tool_call in msg["tool_calls"]:
                tool_calls.append({
                    "tool_name": tool_call.get("name", "unknown"),
                    "args": str(tool_call.get("args", {})),
                })
    
    return tool_calls


__all__ = [
    "format_markdown_report",
    "format_simple_output",
    "extract_tool_calls",
]

