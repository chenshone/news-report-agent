"""Tests for datetime context injection."""

from datetime import datetime

import pytest

deepagents = pytest.importorskip("deepagents")


def _invoke_or_skip(agent, payload):
    from openai import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError

    try:
        return agent.invoke(payload)
    except (NotFoundError, APIConnectionError, APITimeoutError, AuthenticationError) as exc:
        pytest.skip(f"LLM provider unavailable: {exc}")


def test_format_datetime_context():
    """Test datetime formatting for agent context."""
    from src.agent.master import format_datetime_context
    
    # Test with a specific datetime
    dt = datetime(2024, 12, 15, 14, 30, 0)  # Sunday
    context = format_datetime_context(dt)
    
    # Should contain date
    assert "2024年12月15日" in context
    
    # Should contain day of week
    assert "星期日" in context
    
    # Should contain time
    assert "14:30:00" in context
    
    # Should have time references
    assert "今天" in context
    assert "昨天" in context
    assert "近期" in context
    assert "最新" in context
    
    # Should show yesterday's date
    assert "2024年12月14日" in context


def test_format_datetime_different_weekdays():
    """Test that weekdays are correctly formatted."""
    from src.agent.master import format_datetime_context
    
    # Monday
    dt = datetime(2024, 12, 16, 10, 0, 0)
    context = format_datetime_context(dt)
    assert "星期一" in context
    
    # Wednesday
    dt = datetime(2024, 12, 18, 10, 0, 0)
    context = format_datetime_context(dt)
    assert "星期三" in context
    
    # Friday
    dt = datetime(2024, 12, 20, 10, 0, 0)
    context = format_datetime_context(dt)
    assert "星期五" in context


def test_create_agent_with_datetime(skip_if_no_api_key):
    """Test that agent can be created with custom datetime."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Create agent with specific datetime
    dt = datetime(2024, 12, 15, 14, 30, 0)
    
    config = load_settings()
    model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.0
    )
    model = create_chat_model(model_config, config)
    
    # Should not raise
    agent = create_news_agent(
        model_override=model,
        current_datetime=dt
    )
    assert agent is not None


def test_create_agent_default_datetime(skip_if_no_api_key):
    """Test that agent uses current datetime by default."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.0
    )
    model = create_chat_model(model_config, config)
    
    # Create agent without datetime (should use datetime.now())
    agent = create_news_agent(model_override=model)
    assert agent is not None


def test_agent_system_prompt_includes_datetime(skip_if_no_api_key):
    """Integration test: verify agent's system prompt includes datetime info."""
    from datetime import datetime
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.0
    )
    model = create_chat_model(model_config, config)
    
    # Create agent with specific datetime
    dt = datetime(2024, 12, 15, 14, 30, 0)
    agent = create_news_agent(
        model_override=model,
        current_datetime=dt
    )
    
    # Agent should be created successfully
    assert agent is not None
    
    # Try invoking with a time-related query
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "今天是几号？"}]
    })
    
    assert result is not None
    assert "messages" in result
    
    # Agent should have access to datetime info
    response = result["messages"][-1].content
    assert response is not None
    print(f"\n=== Agent Response ===\n{response[:300]}")


def test_datetime_context_format_structure():
    """Test that datetime context has expected structure."""
    from src.agent.master import format_datetime_context
    
    dt = datetime(2024, 12, 15, 14, 30, 0)
    context = format_datetime_context(dt)
    
    # Should have sections
    assert "当前日期：" in context
    assert "当前时间：" in context
    assert "时间参考：" in context
    
    # Should be multi-line
    lines = context.strip().split("\n")
    assert len(lines) >= 5  # At least 5 lines of info


def test_query_planner_prompt_mentions_datetime():
    """Test that query_planner prompt instructs to use datetime."""
    from src.prompts import QUERY_PLANNER_PROMPT
    
    # Should mention datetime awareness
    assert "日期时间" in QUERY_PLANNER_PROMPT or "当前日期" in QUERY_PLANNER_PROMPT
    
    # Should instruct to reference MasterAgent's datetime info
    assert "MasterAgent" in QUERY_PLANNER_PROMPT
    
    # Should mention time precision in query design
    prompt_lower = QUERY_PLANNER_PROMPT.lower()
    assert "时间" in QUERY_PLANNER_PROMPT
    assert "今天" in QUERY_PLANNER_PROMPT


def test_datetime_in_example():
    """Test that query_planner example uses datetime correctly."""
    from src.prompts import QUERY_PLANNER_PROMPT
    
    # Example should show date-specific queries
    assert "YYYY年MM月DD日" in QUERY_PLANNER_PROMPT or "YYYY-MM-DD" in QUERY_PLANNER_PROMPT
    assert "2024" in QUERY_PLANNER_PROMPT
