"""报告模板测试"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


class TestFormatMarkdownReport:
    """测试 Markdown 报告格式化"""
    
    def test_basic_report_structure(self):
        """测试基本报告结构"""
        from src.utils.templates import format_markdown_report
        
        result = {
            "messages": [
                MagicMock(type="ai", content="这是报告内容")
            ]
        }
        
        report = format_markdown_report(
            query="测试查询",
            result=result,
            generation_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        # 验证报告包含必要元素
        assert "# 热点资讯分析报告" in report
        assert "测试查询" in report
        assert "2024年01月01日 12:00:00" in report
        assert "这是报告内容" in report
        assert "本报告由 AI Agent 自动生成" in report
    
    def test_report_with_multiple_messages(self):
        """测试包含多条消息的报告"""
        from src.utils.templates import format_markdown_report
        
        result = {
            "messages": [
                MagicMock(type="user", content="用户查询"),
                MagicMock(type="ai", content="第一条回复"),
                MagicMock(type="ai", content="最终报告内容")  # 应该使用最后一条
            ]
        }
        
        report = format_markdown_report("查询", result)
        
        # 应该包含最后一条 AI 消息
        assert "最终报告内容" in report
        # 不应该包含之前的消息
        assert "第一条回复" not in report
    
    def test_report_with_dict_messages(self):
        """测试字典格式的消息"""
        from src.utils.templates import format_markdown_report
        
        result = {
            "messages": [
                {"role": "user", "content": "用户查询"},
                {"role": "assistant", "content": "AI 回复"}
            ]
        }
        
        report = format_markdown_report("查询", result)
        assert "AI 回复" in report
    
    def test_report_with_empty_messages(self):
        """测试空消息列表"""
        from src.utils.templates import format_markdown_report
        
        result = {"messages": []}
        report = format_markdown_report("查询", result)
        
        # 应该有默认消息
        assert "Agent 运行完成" in report or "未生成报告内容" in report
    
    def test_report_with_no_generation_time(self):
        """测试不提供生成时间的情况"""
        from src.utils.templates import format_markdown_report
        
        result = {
            "messages": [MagicMock(type="ai", content="内容")]
        }
        
        # 应该使用当前时间，不应抛出异常
        report = format_markdown_report("查询", result)
        assert "# 热点资讯分析报告" in report


class TestFormatSimpleOutput:
    """测试简单输出格式化"""
    
    def test_extract_ai_message(self):
        """测试提取 AI 消息"""
        from src.utils.templates import format_simple_output
        
        result = {
            "messages": [
                MagicMock(type="user", content="用户输入"),
                MagicMock(type="ai", content="AI 输出")
            ]
        }
        
        output = format_simple_output(result)
        assert output == "AI 输出"
    
    def test_extract_dict_message(self):
        """测试提取字典格式消息"""
        from src.utils.templates import format_simple_output
        
        result = {
            "messages": [
                {"role": "user", "content": "输入"},
                {"role": "assistant", "content": "输出"}
            ]
        }
        
        output = format_simple_output(result)
        assert output == "输出"
    
    def test_extract_last_ai_message(self):
        """测试提取最后一条 AI 消息"""
        from src.utils.templates import format_simple_output
        
        result = {
            "messages": [
                MagicMock(type="ai", content="第一条"),
                MagicMock(type="ai", content="最后一条")
            ]
        }
        
        output = format_simple_output(result)
        assert output == "最后一条"
    
    def test_empty_messages(self):
        """测试空消息"""
        from src.utils.templates import format_simple_output
        
        result = {"messages": []}
        output = format_simple_output(result)
        
        assert "未生成输出内容" in output or "Agent 运行完成" in output


class TestExtractToolCalls:
    """测试工具调用提取"""
    
    def test_extract_from_messages(self):
        """测试从消息中提取工具调用"""
        from src.utils.templates import extract_tool_calls
        
        # Mock 消息with tool_calls
        msg = MagicMock()
        msg.tool_calls = [
            {"name": "internet_search", "args": {"query": "test"}},
            {"name": "fetch_page", "args": {"url": "http://example.com"}}
        ]
        
        result = {"messages": [msg]}
        tool_calls = extract_tool_calls(result)
        
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool_name"] == "internet_search"
        assert tool_calls[1]["tool_name"] == "fetch_page"
    
    def test_extract_from_dict_messages(self):
        """测试从字典消息中提取工具调用"""
        from src.utils.templates import extract_tool_calls
        
        result = {
            "messages": [
                {
                    "tool_calls": [
                        {"name": "test_tool", "args": {"param": "value"}}
                    ]
                }
            ]
        }
        
        tool_calls = extract_tool_calls(result)
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool_name"] == "test_tool"
    
    def test_no_tool_calls(self):
        """测试没有工具调用的情况"""
        from src.utils.templates import extract_tool_calls
        
        result = {
            "messages": [
                MagicMock(type="user", content="test")
            ]
        }
        
        # Mock 没有 tool_calls 属性
        for msg in result["messages"]:
            msg.tool_calls = []
        
        tool_calls = extract_tool_calls(result)
        assert len(tool_calls) == 0
    
    def test_empty_messages(self):
        """测试空消息列表"""
        from src.utils.templates import extract_tool_calls
        
        result = {"messages": []}
        tool_calls = extract_tool_calls(result)
        assert len(tool_calls) == 0

