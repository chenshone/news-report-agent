"""CLI 主模块测试"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestCLIArgumentParsing:
    """测试命令行参数解析"""
    
    def test_parse_basic_query(self):
        """测试基本查询参数"""
        from cli.main import parse_args
        
        with patch('sys.argv', ['cli.main', '今天有什么新闻']):
            args = parse_args()
            assert args.query == '今天有什么新闻'
            assert args.domain is None
            assert args.output is None
            assert args.verbose is False
    
    def test_parse_with_domain(self):
        """测试带领域参数"""
        from cli.main import parse_args
        
        with patch('sys.argv', ['cli.main', '--domain', 'technology', '科技新闻']):
            args = parse_args()
            assert args.query == '科技新闻'
            assert args.domain == 'technology'
    
    def test_parse_with_output(self):
        """测试带输出文件参数"""
        from cli.main import parse_args
        
        with patch('sys.argv', ['cli.main', '--output', './report.md', 'test query']):
            args = parse_args()
            assert args.query == 'test query'
            assert args.output == './report.md'
    
    def test_parse_with_verbose(self):
        """测试详细日志参数"""
        from cli.main import parse_args
        
        with patch('sys.argv', ['cli.main', '--verbose', 'test']):
            args = parse_args()
            assert args.verbose is True
    
    def test_parse_with_model_override(self):
        """测试模型覆盖参数"""
        from cli.main import parse_args
        
        with patch('sys.argv', ['cli.main', '--model', 'gpt-4o', 'test']):
            args = parse_args()
            assert args.model == 'gpt-4o'


class TestRunAgent:
    """测试 Agent 运行功能"""
    
    @patch('cli.main.load_settings')
    @patch('cli.main.create_news_agent')
    def test_run_agent_basic(self, mock_create_agent, mock_load_settings):
        """测试基本的 Agent 运行"""
        from cli.main import run_agent
        
        # Mock 配置
        mock_config = MagicMock()
        mock_load_settings.return_value = mock_config
        
        # Mock Agent
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "test query"},
                {"role": "assistant", "content": "test response"}
            ]
        }
        mock_create_agent.return_value = mock_agent
        
        # 运行
        result = run_agent("test query")
        
        # 验证
        assert result is not None
        assert "messages" in result
        mock_create_agent.assert_called_once_with(config=mock_config)
        mock_agent.invoke.assert_called_once()
    
    @patch('cli.main.load_settings')
    @patch('cli.main.create_news_agent')
    def test_run_agent_with_domain(self, mock_create_agent, mock_load_settings):
        """测试带领域的 Agent 运行"""
        from cli.main import run_agent
        
        mock_config = MagicMock()
        mock_load_settings.return_value = mock_config
        
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": []}
        mock_create_agent.return_value = mock_agent
        
        run_agent("test query", domain="technology")
        
        # 验证调用参数中包含领域信息
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        assert "[领域: technology]" in messages[0]["content"]


class TestReportFormatting:
    """测试报告格式化功能"""
    
    def test_format_markdown_report(self):
        """测试 Markdown 报告生成"""
        from src.utils.templates import format_markdown_report
        from datetime import datetime
        
        result = {
            "messages": [
                MagicMock(type="user", content="test query"),
                MagicMock(type="ai", content="# Analysis\n\nThis is the report content.")
            ]
        }
        
        report = format_markdown_report(
            query="test query",
            result=result,
            generation_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert "# 热点资讯分析报告" in report
        assert "test query" in report
        assert "Analysis" in report
        assert "2024年01月01日" in report
    
    def test_format_simple_output(self):
        """测试简单文本输出"""
        from src.utils.templates import format_simple_output
        
        result = {
            "messages": [
                MagicMock(type="user", content="query"),
                MagicMock(type="ai", content="response content")
            ]
        }
        
        output = format_simple_output(result)
        assert "response content" in output
    
    def test_format_empty_result(self):
        """测试空结果的处理"""
        from src.utils.templates import format_simple_output
        
        result = {"messages": []}
        output = format_simple_output(result)
        assert "未生成输出内容" in output or "Agent 运行完成" in output


class TestCLIIntegration:
    """CLI 集成测试（使用真实 Agent，需要 API keys）"""
    
    @pytest.mark.skip(reason="需要真实 API keys，作为手动验证用例")
    def test_cli_help(self):
        """测试 CLI 帮助信息"""
        import subprocess
        
        result = subprocess.run(
            ["python", "-m", "cli.main", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "热点资讯聚合" in result.stdout
        assert "--domain" in result.stdout
        assert "--output" in result.stdout
    
    @pytest.mark.skip(reason="需要真实 API keys，作为手动验证用例")
    def test_cli_basic_run(self, tmp_path):
        """测试基本的 CLI 运行"""
        import subprocess
        
        output_file = tmp_path / "report.md"
        
        result = subprocess.run(
            ["python", "-m", "cli.main", "--output", str(output_file), "测试查询"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "热点资讯分析报告" in content

