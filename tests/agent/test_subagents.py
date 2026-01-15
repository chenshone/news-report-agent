"""Tests for expert subagent configurations."""

import pytest

deepagents = pytest.importorskip("deepagents")


def _subagent_field(subagent, field, default=None):
    if isinstance(subagent, dict):
        return subagent.get(field, default)
    if hasattr(subagent, field):
        return getattr(subagent, field)
    if hasattr(subagent, "get"):
        return subagent.get(field, default)
    return default


def test_get_subagent_configs():
    """Test that subagent configurations are correctly loaded."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Should include direct experts + council + report_synthesizer
    assert len(subagents) == 8
    
    # Extract names
    names = [_subagent_field(s, "name") for s in subagents]
    
    # Verify all expected experts are present
    assert "query_planner" in names
    assert "summarizer" in names
    assert "fact_checker" in names
    assert "researcher" in names
    assert "impact_assessor" in names
    assert "expert_supervisor" in names
    assert "expert_council" in names
    
    # Verify query_planner is first (most important)
    assert _subagent_field(subagents[0], "name") == "query_planner"
    
    # Verify expert_council is last (裁决在最后)
    assert _subagent_field(subagents[-1], "name") == "expert_council"


def test_subagent_structure():
    """Test that each subagent has required fields."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from langchain_core.language_models import BaseChatModel
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    for subagent in subagents:
        # Required fields
        name = _subagent_field(subagent, "name")
        description = _subagent_field(subagent, "description")
        assert name
        assert description
        
        # Verify types
        assert isinstance(name, str)
        assert isinstance(description, str)

        runnable = _subagent_field(subagent, "runnable")
        if runnable is not None:
            continue

        system_prompt = _subagent_field(subagent, "system_prompt")
        tools = _subagent_field(subagent, "tools")
        model = _subagent_field(subagent, "model")
        assert isinstance(system_prompt, str)
        assert isinstance(tools, list)
        assert isinstance(model, BaseChatModel)
        
        # Verify system_prompt is not empty
        assert len(system_prompt) > 100, f"{name} prompt too short"


def test_query_planner_config():
    """Test query_planner specific configuration."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find query_planner
    query_planner = next(s for s in subagents if _subagent_field(s, "name") == "query_planner")
    
    # Should not have tools (pure reasoning)
    tools = _subagent_field(query_planner, "tools")
    if tools is not None:
        assert tools == []
    
    # Description should mention query generation
    description = _subagent_field(query_planner, "description")
    assert "查询" in description or "query" in description.lower()
    
    # System prompt should mention reflection
    prompt = _subagent_field(query_planner, "system_prompt")
    if prompt:
        assert "反思" in prompt or "reflection" in prompt.lower()
        assert "查询" in prompt or "query" in prompt.lower()


def test_fact_checker_has_search_tool():
    """Test that fact_checker has verification tools."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from src.tools import internet_search
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find fact_checker
    fact_checker = next(s for s in subagents if _subagent_field(s, "name") == "fact_checker")
    
    # Should have multiple verification tools
    tools = _subagent_field(fact_checker, "tools")
    tool_names = [tool.name for tool in tools]
    assert "internet_search" in tool_names
    assert "search_hackernews" in tool_names
    assert "fetch_page" in tool_names


def test_researcher_has_search_tool():
    """Test that researcher has multi-source research tools."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from src.tools import internet_search
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find researcher
    researcher = next(s for s in subagents if _subagent_field(s, "name") == "researcher")
    
    # Should have multiple research tools
    tools = _subagent_field(researcher, "tools")
    tool_names = [tool.name for tool in tools]
    assert "internet_search" in tool_names
    assert "search_arxiv" in tool_names
    assert "search_github_repos" in tool_names
    assert "fetch_page" in tool_names


def test_summarizer_no_tools():
    """Test that summarizer doesn't need external tools."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find summarizer
    summarizer = next(s for s in subagents if _subagent_field(s, "name") == "summarizer")
    
    # Should not have tools
    tools = _subagent_field(summarizer, "tools")
    if tools is not None:
        assert tools == []


def test_subagent_model_format():
    """Test that subagent models are properly configured BaseChatModel instances."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from langchain_core.language_models import BaseChatModel
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    for subagent in subagents:
        model = _subagent_field(subagent, "model")
        if model is None:
            continue
        
        # Should be a BaseChatModel instance
        name = _subagent_field(subagent, "name")
        assert isinstance(model, BaseChatModel), f"{name} model should be BaseChatModel instance"


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
        name = _subagent_field(subagent, "name")
        prompt = _subagent_field(subagent, "system_prompt")
        if not prompt:
            continue
        
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
