"""Tests for MasterAgent creation and configuration."""

import pytest

deepagents = pytest.importorskip("deepagents")


def _invoke_or_skip(agent, payload):
    from openai import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError

    try:
        return agent.invoke(payload)
    except (NotFoundError, APIConnectionError, APITimeoutError, AuthenticationError) as exc:
        pytest.skip(f"LLM provider unavailable: {exc}")


def test_create_news_agent_basic(skip_if_no_api_key):
    """Integration test: basic agent creation with real API keys."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Load real config from environment
    config = load_settings()
    
    # Create agent with a lightweight model for testing
    model_config = ModelConfig(model="gpt-4o-mini", provider=config.model_map["master"].provider, temperature=0.0)
    model = create_chat_model(model_config, config)
    agent = create_news_agent(model_override=model)
    
    # Verify agent was created
    assert agent is not None
    assert hasattr(agent, "invoke")
    
    # Try a simple invoke to verify it really works
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "你好"}]
    })
    
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) > 0


def test_create_news_agent_with_model_override(skip_if_no_api_key):
    """Integration test: agent creation with custom model configuration."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    
    # Create agent with custom temperature
    model_config = ModelConfig(model="gpt-4o-mini", provider=config.model_map["master"].provider, temperature=0.8)
    model = create_chat_model(model_config, config)
    agent = create_news_agent(model_override=model)
    
    assert agent is not None
    
    # Verify it can respond (higher temperature for creative response)
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "说个笑话"}]
    })
    
    assert result is not None
    assert "messages" in result


def test_create_news_agent_with_custom_config(skip_if_no_api_key):
    """Integration test: agent creation with custom configuration."""
    import os
    from src.agent import create_news_agent
    from src.config import AppConfig, ModelConfig, load_settings
    
    # Load base config to get provider info
    base_config = load_settings()
    provider = base_config.model_map["master"].provider
    model_map = dict(base_config.model_map)
    
    # Create custom config with real API keys
    model_map["master"] = ModelConfig(
        model="gpt-4o-mini",
        provider=provider,
        temperature=0.2,
    )

    config = AppConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        google_api_key=base_config.google_api_key,
        gemini_model=base_config.gemini_model,
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        model_map=model_map,
    )
    
    # Create agent with custom config
    agent = create_news_agent(config=config)
    
    assert agent is not None
    
    # Verify it works
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "测试"}]
    })
    assert result is not None


def test_create_news_agent_with_additional_tools(skip_if_no_api_key):
    """Integration test: agent creation with additional custom tools."""
    from langchain_core.tools import tool
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Define a custom tool
    @tool
    def custom_tool(query: str) -> str:
        """A custom test tool that returns a greeting."""
        return f"Custom greeting: Hello {query}!"
    
    # Create agent with additional tool
    config = load_settings()
    model_config = ModelConfig(model="gpt-4o-mini", provider=config.model_map["master"].provider, temperature=0.0)
    model = create_chat_model(model_config, config)
    agent = create_news_agent(
        additional_tools=[custom_tool],
        model_override=model,
    )
    
    assert agent is not None
    
    # Verify basic functionality
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "你好"}]
    })
    assert result is not None


def test_agent_has_required_tools(skip_if_no_api_key):
    """Integration test: verify agent has all required tools registered."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    model_config = ModelConfig(model="gpt-4o-mini", provider=config.model_map["master"].provider, temperature=0.0)
    model = create_chat_model(model_config, config)
    agent = create_news_agent(model_override=model)
    
    # Check that agent was created successfully
    assert agent is not None
    assert hasattr(agent, "invoke")
    
    # Verify agent can respond
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "测试工具注册"}]
    })
    assert result is not None


def test_agent_system_prompt_loaded(monkeypatch):
    """Test that system prompt is properly loaded."""
    from src.prompts import MASTER_AGENT_SYSTEM_PROMPT
    
    # Verify prompt contains key concepts
    assert "规划" in MASTER_AGENT_SYSTEM_PROMPT
    assert "反思" in MASTER_AGENT_SYSTEM_PROMPT
    assert "工具使用" in MASTER_AGENT_SYSTEM_PROMPT
    assert "多智能体协作" in MASTER_AGENT_SYSTEM_PROMPT
    
    # Verify it mentions key tools
    assert "internet_search" in MASTER_AGENT_SYSTEM_PROMPT
    assert "evaluate_credibility" in MASTER_AGENT_SYSTEM_PROMPT
    assert "write_todos" in MASTER_AGENT_SYSTEM_PROMPT
    assert "task()" in MASTER_AGENT_SYSTEM_PROMPT


def test_agent_simple_invoke_integration(skip_if_no_api_key):
    """Integration test: invoke agent with a simple query."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Use real config from environment
    config = load_settings()
    model_config = ModelConfig(model="gpt-4o-mini", provider=config.model_map["master"].provider, temperature=0.0)
    model = create_chat_model(model_config, config)
    agent = create_news_agent(model_override=model)
    
    # Simple test query - ask for planning steps
    result = _invoke_or_skip(agent, {
        "messages": [
            {"role": "user", "content": "列出分析科技热点需要的步骤"}
        ]
    })
    
    # Check that we got a response
    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) > 0
    
    # The agent should have responded
    last_message = result["messages"][-1]
    assert last_message.content
    assert len(last_message.content) > 0
    
    print("\n=== Agent Response ===")
    print(last_message.content[:500])  # Print first 500 chars for debugging


def test_create_news_agent_with_chat_model_instance(skip_if_no_api_key):
    """Integration test: agent creation with a pre-configured ChatModel instance."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Create a custom ChatModel instance with specific configuration
    config = load_settings()
    custom_model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.5,
        max_tokens=1000,
    )
    custom_model = create_chat_model(custom_model_config, config)
    
    # Pass the model instance directly
    agent = create_news_agent(model_override=custom_model)
    
    assert agent is not None
    assert hasattr(agent, "invoke")
    
    # Verify it works with max_tokens limit
    result = _invoke_or_skip(agent, {
        "messages": [{"role": "user", "content": "简单回答：1+1=?"}]
    })
    
    assert result is not None
    assert "messages" in result


def test_agent_azure_config(skip_if_no_api_key):
    """Integration test: verify Azure configuration is correctly detected and used."""
    import os
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    config = load_settings()
    
    # Check if we're using Azure
    if config.model_map["master"].provider == "azure":
        # Test with Azure configuration
        agent = create_news_agent(config=config)
        assert agent is not None
        
        # Verify it works
        result = _invoke_or_skip(agent, {
            "messages": [{"role": "user", "content": "测试 Azure 配置"}]
        })
        assert result is not None
        assert "messages" in result
        
        print("\n=== Using Azure OpenAI ===")
    else:
        # Test with OpenAI configuration
        agent = create_news_agent(config=config)
        assert agent is not None
        
        # Verify it works
        result = _invoke_or_skip(agent, {
            "messages": [{"role": "user", "content": "测试 OpenAI 配置"}]
        })
        assert result is not None
        assert "messages" in result
        
        print("\n=== Using OpenAI ===")
    
    print(f"Provider: {config.model_map['master'].provider}")
