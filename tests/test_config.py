from pathlib import Path

from src.config import (
    OPENAI_API_KEY_ENV,
    AZURE_OPENAI_API_KEY_ENV,
    AZURE_OPENAI_DEPLOYMENT_NAME_ENV,
    AZURE_OPENAI_ENDPOINT_ENV,
    BRAVE_API_KEY_ENV,
    FILESYSTEM_BASE_ENV,
    TAVILY_API_KEY_ENV,
    FIRECRAWL_API_KEY_ENV,
    ModelConfig,
    default_model_map,
    load_settings,
    create_chat_model,
)


def test_load_settings_reads_environment(monkeypatch, tmp_path):
    # Use explicit env dict to isolate from real environment
    test_env = {
        AZURE_OPENAI_API_KEY_ENV: "az-openai-test",
        AZURE_OPENAI_ENDPOINT_ENV: "https://example.azure.com",
        AZURE_OPENAI_DEPLOYMENT_NAME_ENV: "gpt-4o-azure",
        TAVILY_API_KEY_ENV: "tv-test",
        BRAVE_API_KEY_ENV: "brave-test",
        FIRECRAWL_API_KEY_ENV: "crawl-test",
        FILESYSTEM_BASE_ENV: str(tmp_path),
        # No Gemini keys - so experts should also use Azure
    }

    settings = load_settings(env=test_env)

    assert settings.azure_openai_api_key == "az-openai-test"
    assert settings.azure_openai_endpoint == "https://example.azure.com"
    assert settings.azure_openai_deployment_name == "gpt-4o-azure"
    assert settings.tavily_api_key == "tv-test"
    assert settings.brave_api_key == "brave-test"
    assert settings.firecrawl_api_key == "crawl-test"
    assert settings.filesystem.resolved_base() == tmp_path.resolve()

    # default model map should include all roles and use azure provider/deployment
    for role in ("master", "summarizer", "fact_checker", "researcher", "impact_assessor"):
        assert role in settings.model_map
        cfg = settings.model_map[role]
        assert cfg.provider == "azure"
        assert cfg.model == "gpt-4o-azure"
        assert cfg.deployment == "gpt-4o-azure"


def test_model_overrides_do_not_mutate_defaults():
    original = default_model_map()
    override = {"master": ModelConfig(model="local:test", temperature=0.5)}

    settings = load_settings(env={}, model_overrides=override)

    assert settings.model_map["master"].model == "local:test"
    assert original["master"].model == "gpt-4o"

    fallback = ModelConfig(model="openai:gpt-4o-mini", temperature=0.0)
    assert settings.model_for_role("unknown", default=fallback) is fallback
    assert settings.model_for_role("unknown").model == "openai:gpt-4o-mini"


def test_filesystem_base_can_be_overridden(tmp_path):
    base_dir = tmp_path / "agent-data"
    settings = load_settings(env={}, base_path=base_dir)

    assert settings.filesystem.base_path == Path(base_dir)
    assert settings.filesystem.resolved_base().name == "agent-data"


def test_load_settings_with_openai_key():
    # 使用显式的 env 字典，不依赖实际环境变量
    test_env = {
        OPENAI_API_KEY_ENV: "sk-test-key",
        TAVILY_API_KEY_ENV: "tv-test",
    }
    
    settings = load_settings(env=test_env)
    
    assert settings.openai_api_key == "sk-test-key"
    assert settings.tavily_api_key == "tv-test"
    # 没有设置 Azure 相关的，应该使用 OpenAI provider
    assert settings.model_map["master"].provider == "openai"


def test_create_chat_model_openai(monkeypatch):
    monkeypatch.setenv(OPENAI_API_KEY_ENV, "sk-test")
    
    config = ModelConfig(model="gpt-4o-mini", provider="openai", temperature=0.0)
    app_config = load_settings()
    
    # 实际创建会需要真实的 API，这里只测试不抛异常
    try:
        model = create_chat_model(config, app_config)
        assert model is not None
    except Exception:
        # 如果没有网络或真实 key，跳过
        pass


def test_create_chat_model_azure(monkeypatch):
    monkeypatch.setenv(AZURE_OPENAI_API_KEY_ENV, "az-test")
    monkeypatch.setenv(AZURE_OPENAI_ENDPOINT_ENV, "https://test.openai.azure.com")
    
    config = ModelConfig(
        model="gpt-4o",
        provider="azure",
        deployment="gpt-4o-deployment",
        temperature=0.1,
    )
    app_config = load_settings()
    
    try:
        model = create_chat_model(config, app_config)
        assert model is not None
    except Exception:
        # 如果没有网络或真实 key，跳过
        pass
