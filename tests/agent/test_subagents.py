"""Tests for expert subagent configurations."""

import pytest

deepagents = pytest.importorskip("deepagents")


def test_get_subagent_configs():
    """Test that subagent configurations are correctly loaded."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Should have 6 experts (including supervisor)
    assert len(subagents) == 6
    
    # Extract names
    names = [s["name"] for s in subagents]
    
    # Verify all expected experts are present
    assert "query_planner" in names
    assert "summarizer" in names
    assert "fact_checker" in names
    assert "researcher" in names
    assert "impact_assessor" in names
    assert "expert_supervisor" in names
    
    # Verify query_planner is first (most important)
    assert subagents[0]["name"] == "query_planner"
    
    # Verify expert_supervisor is last (审核在分析之后)
    assert subagents[-1]["name"] == "expert_supervisor"


def test_subagent_structure():
    """Test that each subagent has required fields."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from langchain_core.language_models import BaseChatModel
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    for subagent in subagents:
        # Required fields
        assert "name" in subagent
        assert "description" in subagent
        assert "system_prompt" in subagent
        assert "tools" in subagent
        assert "model" in subagent
        
        # Verify types
        assert isinstance(subagent["name"], str)
        assert isinstance(subagent["description"], str)
        assert isinstance(subagent["system_prompt"], str)
        assert isinstance(subagent["tools"], list)
        assert isinstance(subagent["model"], BaseChatModel)  # Now expecting ChatModel instance
        
        # Verify system_prompt is not empty
        assert len(subagent["system_prompt"]) > 100, f"{subagent['name']} prompt too short"


def test_query_planner_config():
    """Test query_planner specific configuration."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find query_planner
    query_planner = next(s for s in subagents if s["name"] == "query_planner")
    
    # Should not have tools (pure reasoning)
    assert query_planner["tools"] == []
    
    # Description should mention query generation
    assert "查询" in query_planner["description"] or "query" in query_planner["description"].lower()
    
    # System prompt should mention reflection
    prompt = query_planner["system_prompt"]
    assert "反思" in prompt or "reflection" in prompt.lower()
    assert "查询" in prompt or "query" in prompt.lower()


def test_fact_checker_has_search_tool():
    """Test that fact_checker has internet_search tool."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from src.tools import internet_search
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find fact_checker
    fact_checker = next(s for s in subagents if s["name"] == "fact_checker")
    
    # Should have internet_search tool (now checking for tool object)
    assert len(fact_checker["tools"]) > 0
    assert any(tool.name == "internet_search" for tool in fact_checker["tools"])


def test_researcher_has_search_tool():
    """Test that researcher has internet_search tool."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from src.tools import internet_search
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find researcher
    researcher = next(s for s in subagents if s["name"] == "researcher")
    
    # Should have internet_search tool (now checking for tool object)
    assert len(researcher["tools"]) > 0
    assert any(tool.name == "internet_search" for tool in researcher["tools"])


def test_summarizer_no_tools():
    """Test that summarizer doesn't need external tools."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find summarizer
    summarizer = next(s for s in subagents if s["name"] == "summarizer")
    
    # Should not have tools
    assert summarizer["tools"] == []


def test_subagent_model_format():
    """Test that subagent models are properly configured BaseChatModel instances."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from langchain_core.language_models import BaseChatModel
    from langchain_openai import ChatOpenAI, AzureChatOpenAI
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    for subagent in subagents:
        model = subagent["model"]
        
        # Should be a BaseChatModel instance
        assert isinstance(model, BaseChatModel), f"{subagent['name']} model should be BaseChatModel instance"
        
        # Should be either ChatOpenAI or AzureChatOpenAI
        assert isinstance(model, (ChatOpenAI, AzureChatOpenAI)), f"{subagent['name']} model should be ChatOpenAI or AzureChatOpenAI"


def test_agent_with_subagents(skip_if_no_api_key):
    """Integration test: verify agent can be created with subagents."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    
    # Create agent with subagents (using default model from config)
    agent = create_news_agent(config=config)
    
    assert agent is not None
    
    # Just verify agent is created, don't invoke to avoid API costs and deployment issues
    # The fact that create_news_agent succeeded means subagents are properly configured


def test_subagent_prompt_quality():
    """Test that all subagent prompts contain key instructions."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    for subagent in subagents:
        prompt = subagent["system_prompt"]
        name = subagent["name"]
        
        # All prompts should define role/task
        assert "任务" in prompt or "task" in prompt.lower(), f"{name}: missing task definition"
        
        # query_planner should have reflection keywords
        if name == "query_planner":
            assert "反思" in prompt or "reflection" in prompt.lower()
            assert "查询" in prompt or "query" in prompt.lower()
            assert "JSON" in prompt or "json" in prompt.lower()  # Output format
        
        # fact_checker should mention verification
        if name == "fact_checker":
            assert "核查" in prompt or "verify" in prompt.lower() or "fact" in prompt.lower()
        
        # researcher should mention background
        if name == "researcher":
            assert "背景" in prompt or "background" in prompt.lower()
        
        # summarizer should mention extraction
        if name == "summarizer":
            assert "摘要" in prompt or "summary" in prompt.lower() or "要点" in prompt
        
        # impact_assessor should mention impact/influence
        if name == "impact_assessor":
            assert "影响" in prompt or "impact" in prompt.lower()

