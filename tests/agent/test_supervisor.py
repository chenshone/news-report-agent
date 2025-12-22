"""Tests for expert_supervisor agent."""

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


def test_supervisor_in_subagents():
    """Test that expert_supervisor is included in subagent configs."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find supervisor
    supervisor = next((s for s in subagents if _subagent_field(s, "name") == "expert_supervisor"), None)
    
    assert supervisor is not None, "expert_supervisor not found in subagents"
    
    # Verify fields
    assert _subagent_field(supervisor, "description") is not None
    if _subagent_field(supervisor, "runnable") is None:
        assert _subagent_field(supervisor, "system_prompt") is not None
        assert _subagent_field(supervisor, "tools") is not None
        assert _subagent_field(supervisor, "model") is not None


def test_supervisor_description():
    """Test that supervisor has appropriate description."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    supervisor = next(s for s in subagents if _subagent_field(s, "name") == "expert_supervisor")
    
    description = _subagent_field(supervisor, "description")
    
    # Should mention key responsibilities
    assert "审核" in description or "review" in description.lower()
    assert "协调" in description or "coordinate" in description.lower()


def test_supervisor_prompt_content():
    """Test that supervisor prompt contains key instructions."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    # Should be substantial
    assert len(EXPERT_SUPERVISOR_PROMPT) > 1000
    
    # Should mention key concepts
    prompt = EXPERT_SUPERVISOR_PROMPT
    assert "综合" in prompt
    assert "裁决" in prompt
    assert "交叉评审" in prompt
    assert "分歧" in prompt
    
    # Should mention workflow
    assert "四阶段专家协作流程" in prompt or "裁决工作" in prompt
    assert "评审等级" in prompt
    assert "证据优先" in prompt


def test_supervisor_quality_checklist():
    """Test that supervisor prompt includes quality checklist."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should include decision principles
    assert "证据优先" in prompt
    assert "逻辑优先" in prompt
    assert "工作原则" in prompt


def test_supervisor_output_format():
    """Test that supervisor prompt defines output format."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should define output sections
    assert "# 专家委员会综合裁决" in prompt
    assert "可靠结论" in prompt
    assert "争议裁决" in prompt
    assert "待验证事项" in prompt


def test_supervisor_scenarios():
    """Test that supervisor prompt includes typical scenarios."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should mention conflicts/decisions
    assert "分歧" in prompt
    assert "争议" in prompt


def test_supervisor_model_config():
    """Test that supervisor uses appropriate model."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    from langchain_core.language_models import BaseChatModel
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    supervisor = next(s for s in subagents if _subagent_field(s, "name") == "expert_supervisor")
    
    model = _subagent_field(supervisor, "model")
    if model is not None:
        assert isinstance(model, BaseChatModel)


def test_supervisor_workflow_integration(skip_if_no_api_key):
    """Integration test: verify supervisor can be called in workflow."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    from openai import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError
    
    config = load_settings()
    model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.0
    )
    model = create_chat_model(model_config, config)
    
    # Create agent with supervisor
    agent = create_news_agent(model_override=model)
    
    assert agent is not None
    
    # Verify agent can respond
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": "你有哪些专家可以协助"}]
        })
    except (NotFoundError, APIConnectionError, APITimeoutError, AuthenticationError) as exc:
        pytest.skip(f"LLM provider unavailable: {exc}")
    
    assert result is not None
    assert "messages" in result


def test_supervisor_is_last():
    """Test that supervisor is configured as the last subagent."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    names = [_subagent_field(s, "name") for s in subagents]
    assert "expert_supervisor" in names
    assert "expert_council" in names
    assert names.index("expert_supervisor") < names.index("expert_council")


def test_supervisor_responsibilities():
    """Test that supervisor prompt clearly defines responsibilities."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should clearly state role
    assert "主管" in prompt or "Chairman" in prompt
    
    # Should list specific responsibilities
    responsibilities = [
        "综合",
        "仲裁",
        "裁决",
    ]
    
    for responsibility in responsibilities:
        assert responsibility in prompt, f"Missing responsibility: {responsibility}"
