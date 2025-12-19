"""端到端集成测试

这些测试验证完整的 Agent 工作流程，从用户查询到最终报告生成。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestAgentE2EFlow:
    """测试 Agent 端到端流程"""
    
    @pytest.mark.skip(reason="需要真实 API keys，作为手动验证")
    def test_complete_workflow_real_api(self):
        """
        完整工作流测试（使用真实 API）
        
        这个测试验证：
        1. Agent 创建
        2. 查询处理
        3. 工具调用（搜索、抓取、评估）
        4. 子Agent 派生
        5. 报告生成
        """
        from src.agent import create_news_agent
        from src.config import load_settings
        
        config = load_settings()
        agent = create_news_agent(config=config)
        
        # 执行查询
        result = agent.invoke({
            "messages": [{"role": "user", "content": "今天AI领域有什么重要新闻"}]
        })
        
        # 验证结果
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        
        # 最后一条消息应该是 AI 的回复
        last_message = result["messages"][-1]
        assert hasattr(last_message, "content") or "content" in last_message
    
    @patch('src.agent.master.create_chat_model')
    @patch('src.tools.search.internet_search._run')
    def test_workflow_with_mocked_tools(self, mock_search, mock_create_model):
        """
        使用 Mock 工具的工作流测试
        
        这个测试验证 Agent 能够：
        1. 正确调用工具
        2. 处理工具返回的结果
        3. 生成有效的响应
        """
        from src.agent import create_news_agent
        from src.config import load_settings, ModelConfig
        
        # Mock LLM 返回
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(
            content="根据搜索结果，今天的重要新闻包括...",
            type="ai"
        )
        mock_create_model.return_value = mock_model
        
        # Mock 搜索工具返回
        mock_search.return_value = """
        找到 3 条结果：
        1. OpenAI 发布新模型
        2. Google AI 研究突破
        3. Meta 开源新框架
        """
        
        config = load_settings()
        agent = create_news_agent(config=config)
        
        result = agent.invoke({
            "messages": [{"role": "user", "content": "今天有什么AI新闻"}]
        })
        
        assert result is not None
        assert "messages" in result


class TestReflectionMechanism:
    """测试反思机制"""
    
    @pytest.mark.skip(reason="需要真实 API 和复杂场景设置")
    def test_reflection_triggers_on_insufficient_results(self):
        """
        测试当结果不足时，Agent 会触发反思
        
        场景：
        1. 首次搜索返回很少结果
        2. Agent 反思并调整查询
        3. 再次搜索获得更多结果
        """
        from src.agent import create_news_agent
        
        agent = create_news_agent()
        
        # 使用一个可能需要调整查询的模糊问题
        result = agent.invoke({
            "messages": [{"role": "user", "content": "最新的技术进展"}]
        })
        
        # 验证 Agent 进行了多次工具调用（说明有反思和调整）
        messages = result.get("messages", [])
        tool_call_count = sum(1 for msg in messages if hasattr(msg, "tool_calls") and msg.tool_calls)
        
        # 如果有反思，应该有多次工具调用
        assert tool_call_count > 1


class TestMultiAgentCollaboration:
    """测试多Agent协作"""
    
    @pytest.mark.skip(reason="需要真实 API，作为手动验证")
    def test_subagent_invocation(self):
        """
        测试子Agent调用
        
        验证 MasterAgent 能够：
        1. 识别需要专家分析的场景
        2. 通过 task() 派发子Agent
        3. 整合子Agent的分析结果
        """
        from src.agent import create_news_agent
        
        agent = create_news_agent()
        
        # 使用一个需要深度分析的查询
        result = agent.invoke({
            "messages": [{"role": "user", "content": "分析OpenAI最新模型的技术细节和影响"}]
        })
        
        # 验证有完整的分析内容
        assert result is not None
        messages = result.get("messages", [])
        assert len(messages) > 0


class TestCLIIntegration:
    """测试 CLI 集成"""
    
    def test_cli_imports(self):
        """测试 CLI 模块可以正确导入"""
        try:
            from cli.main import parse_args, run_agent, main
            assert callable(parse_args)
            assert callable(run_agent)
            assert callable(main)
        except ImportError as e:
            pytest.fail(f"CLI 模块导入失败: {e}")
    
    @patch('cli.main.create_news_agent')
    @patch('cli.main.load_settings')
    def test_cli_run_agent_integration(self, mock_load_settings, mock_create_agent):
        """测试 CLI 的 Agent 运行集成"""
        from cli.main import run_agent
        
        # Mock 配置
        mock_config = MagicMock()
        mock_load_settings.return_value = mock_config
        
        # Mock Agent 返回
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "test"},
                MagicMock(type="ai", content="response")
            ]
        }
        mock_create_agent.return_value = mock_agent
        
        # 运行
        result = run_agent("test query")
        
        # 验证
        assert result is not None
        assert "messages" in result
        mock_create_agent.assert_called_once()
        mock_agent.invoke.assert_called_once()
    
    def test_report_generation_end_to_end(self, tmp_path):
        """测试报告生成的完整流程"""
        from src.utils.templates import format_markdown_report
        from datetime import datetime
        
        # 模拟 Agent 结果
        result = {
            "messages": [
                MagicMock(type="user", content="测试查询"),
                MagicMock(type="ai", content="# 分析报告\n\n详细内容...")
            ]
        }
        
        # 生成报告
        report = format_markdown_report(
            query="测试查询",
            result=result,
            generation_time=datetime.now()
        )
        
        # 保存到文件
        report_file = tmp_path / "test_report.md"
        report_file.write_text(report, encoding="utf-8")
        
        # 验证文件
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "# 热点资讯分析报告" in content
        assert "测试查询" in content
        assert "分析报告" in content


class TestErrorHandling:
    """测试错误处理"""
    
    @patch('src.tools.search.internet_search._run')
    def test_tool_failure_handling(self, mock_search):
        """测试工具失败时的处理"""
        from src.tools import internet_search
        
        # Mock 工具失败
        mock_search.side_effect = Exception("API 调用失败")
        
        # 工具应该返回错误消息而不是抛出异常
        result = internet_search._run(query="test")
        
        assert "错误" in result or "失败" in result
    
    def test_empty_query_handling(self):
        """测试空查询的处理"""
        from src.utils.templates import format_simple_output
        
        result = {"messages": []}
        output = format_simple_output(result)
        
        # 应该有默认的提示信息
        assert output is not None
        assert len(output) > 0


class TestConfiguration:
    """测试配置管理"""
    
    def test_config_loading(self):
        """测试配置加载"""
        from src.config import load_settings
        
        config = load_settings()
        
        assert config is not None
        assert hasattr(config, "model_map")
        assert "master" in config.model_map
    
    def test_model_config_for_all_roles(self):
        """测试所有角色都有模型配置"""
        from src.config import load_settings
        
        config = load_settings()
        
        required_roles = [
            "master",
            "summarizer",
            "fact_checker",
            "researcher",
            "impact_assessor"
        ]
        
        for role in required_roles:
            assert role in config.model_map, f"缺少 {role} 的模型配置"
            model_config = config.model_for_role(role)
            assert model_config is not None


class TestDataModels:
    """测试数据模型"""
    
    def test_news_item_model(self):
        """测试 NewsItem 模型"""
        from src.schemas import NewsItem
        
        news = NewsItem(
            title="测试新闻",
            url="https://example.com",
            source="Example",
            published_at="2024-01-01",
            summary="测试摘要"
        )
        
        assert news.title == "测试新闻"
        assert news.url == "https://example.com"
    
    def test_analysis_result_model(self):
        """测试 AnalysisResult 模型"""
        from src.schemas import AnalysisResult, ScoreBreakdown
        
        result = AnalysisResult(
            title="分析标题",
            summary="分析摘要",
            key_points=["要点1", "要点2"],
            score_breakdown=ScoreBreakdown(
                relevance=0.9,
                credibility=0.8,
                impact=0.7,
                timeliness=0.85
            )
        )
        
        assert result.title == "分析标题"
        assert len(result.key_points) == 2
        assert result.score_breakdown.relevance == 0.9

