"""Tests for expert_supervisor agent."""

import pytest

deepagents = pytest.importorskip("deepagents")


def test_supervisor_in_subagents():
    """Test that expert_supervisor is included in subagent configs."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Find supervisor
    supervisor = next((s for s in subagents if s["name"] == "expert_supervisor"), None)
    
    assert supervisor is not None, "expert_supervisor not found in subagents"
    
    # Verify fields
    assert "description" in supervisor
    assert "system_prompt" in supervisor
    assert "tools" in supervisor
    assert "model" in supervisor


def test_supervisor_description():
    """Test that supervisor has appropriate description."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    supervisor = next(s for s in subagents if s["name"] == "expert_supervisor")
    
    description = supervisor["description"]
    
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
    assert "审核" in prompt
    assert "一致性" in prompt or "consistency" in prompt.lower()
    assert "完整性" in prompt or "completeness" in prompt.lower()
    assert "准确性" in prompt or "accuracy" in prompt.lower()
    
    # Should mention file paths
    assert "/analysis/" in prompt
    assert "supervisor" in prompt
    
    # Should mention workflow
    assert "工作流程" in prompt or "workflow" in prompt.lower()
    assert "问题" in prompt
    assert "修正" in prompt or "revision" in prompt.lower()


def test_supervisor_quality_checklist():
    """Test that supervisor prompt includes quality checklist."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should have check items
    assert "一致性检查" in prompt
    assert "完整性检查" in prompt
    assert "准确性检查" in prompt
    assert "深度检查" in prompt


def test_supervisor_output_format():
    """Test that supervisor prompt defines output format."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should define two output scenarios
    assert "需要修正" in prompt
    assert "通过" in prompt or "批准" in prompt
    
    # Should mention file outputs
    assert "issues.md" in prompt
    assert "approval.md" in prompt
    assert "integration_guide.md" in prompt


def test_supervisor_scenarios():
    """Test that supervisor prompt includes typical scenarios."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should have example scenarios
    assert "场景" in prompt or "scenario" in prompt.lower()
    assert "事实矛盾" in prompt or "fact" in prompt.lower()


def test_supervisor_model_config():
    """Test that supervisor uses appropriate model."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    supervisor = next(s for s in subagents if s["name"] == "expert_supervisor")
    
    # Should use a strong model (same as master)
    model = supervisor["model"]
    assert ":" in model  # Format: provider:model
    
    # Should not be a mini model (needs strong reasoning)
    assert "mini" not in model.lower()


def test_supervisor_workflow_integration(skip_if_no_api_key):
    """Integration test: verify supervisor can be called in workflow."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
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
    result = agent.invoke({
        "messages": [{"role": "user", "content": "你有哪些专家可以协助"}]
    })
    
    assert result is not None
    assert "messages" in result


def test_supervisor_is_last():
    """Test that supervisor is configured as the last subagent."""
    from src.agent.subagents import get_subagent_configs
    from src.config import load_settings
    
    config = load_settings()
    subagents = get_subagent_configs(config)
    
    # Supervisor should be last (called after all other experts)
    assert subagents[-1]["name"] == "expert_supervisor"


def test_supervisor_responsibilities():
    """Test that supervisor prompt clearly defines responsibilities."""
    from src.prompts import EXPERT_SUPERVISOR_PROMPT
    
    prompt = EXPERT_SUPERVISOR_PROMPT
    
    # Should clearly state role
    assert "总编辑" in prompt or "质量" in prompt
    
    # Should list specific responsibilities
    responsibilities = [
        "审核",
        "发现",
        "协调",
        "修正",
        "确认"
    ]
    
    for responsibility in responsibilities:
        assert responsibility in prompt, f"Missing responsibility: {responsibility}"

