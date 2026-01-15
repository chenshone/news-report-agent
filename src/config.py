"""Configuration utilities for the news report agent (Pydantic v2)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

# Environment variable names
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
AZURE_OPENAI_API_KEY_ENV = "AZURE_OPENAI_API_KEY"
AZURE_OPENAI_ENDPOINT_ENV = "AZURE_OPENAI_ENDPOINT"
AZURE_OPENAI_DEPLOYMENT_NAME_ENV = "AZURE_OPENAI_DEPLOYMENT_NAME"
GOOGLE_API_KEY_ENV = "GEMINI_KEY"
GEMINI_MODEL_ENV = "MODEL_GEMINI_3_FLASH"
TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
BRAVE_API_KEY_ENV = "BRAVE_API_KEY"
FIRECRAWL_API_KEY_ENV = "FIRECRAWL_API_KEY"
FILESYSTEM_BASE_ENV = "NEWS_AGENT_FS_BASE"


class ModelConfig(BaseModel):
    """Model settings for an agent role."""

    model_config = ConfigDict(frozen=True)

    model: str
    provider: str = "openai"
    deployment: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None

    def to_dict(self) -> dict[str, object]:
        return self.model_dump()


class FilesystemConfig(BaseModel):
    """Filesystem configuration for persisting agent outputs."""

    base_path: Path = Field(default=Path("./data"))

    def resolved_base(self) -> Path:
        return self.base_path.expanduser().resolve()


class AppConfig(BaseModel):
    """Application-wide configuration loaded from the environment."""

    model_config = ConfigDict(frozen=False)

    openai_api_key: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    google_api_key: str | None = None
    gemini_model: str | None = None
    tavily_api_key: str | None = None
    brave_api_key: str | None = None
    firecrawl_api_key: str | None = None
    filesystem: FilesystemConfig = Field(default_factory=FilesystemConfig)
    model_map: dict[str, ModelConfig] = Field(default_factory=dict)

    def model_for_role(
        self, role: str, default: ModelConfig | None = None
    ) -> ModelConfig:
        """Return the configured model for a given role."""
        if role in self.model_map:
            return self.model_map[role]
        if default is not None:
            return default
        return ModelConfig(model="openai:gpt-4o-mini", temperature=0.0)


def default_model_map(
    provider: str = "openai",
    deployment: str | None = None,
    expert_provider: str | None = None,
    expert_model: str | None = None,
) -> dict[str, ModelConfig]:
    """
    Default model configuration per role.

    If provider == "azure", the deployment name is used for all roles.
    If expert_provider/expert_model is set, expert agents use that configuration.
    """
    # Role configurations: (default_model, temperature)
    role_configs = {
        "master": ("gpt-4o", 0.1),
        "summarizer": ("gpt-4o-mini", 0.0),
        "fact_checker": ("gpt-4o", 0.0),
        "researcher": ("gpt-4o", 0.2),
        "impact_assessor": ("gpt-4o", 0.3),
    }

    result: dict[str, ModelConfig] = {}
    use_expert_config = expert_model and expert_provider

    for role, (default_model, temp) in role_configs.items():
        is_master = role == "master"

        if not is_master and use_expert_config:
            result[role] = ModelConfig(
                model=expert_model,
                provider=expert_provider,
                temperature=temp,
            )
        else:
            result[role] = ModelConfig(
                model=deployment or default_model,
                provider=provider,
                deployment=deployment,
                temperature=temp,
            )

    return result


def load_settings(
    env: Mapping[str, str] | None = None,
    base_path: str | Path | None = None,
    model_overrides: Mapping[str, ModelConfig] | None = None,
) -> AppConfig:
    """
    Load application settings from environment variables with sensible defaults.

    Args:
        env: Optional mapping used for testing; defaults to os.environ.
        base_path: Override the filesystem base directory.
        model_overrides: Optional mapping to override per-role model config.
    """
    load_dotenv(override=False)
    source = env if env is not None else os.environ

    fs_base = Path(base_path or source.get(FILESYSTEM_BASE_ENV, "./data"))

    use_azure = bool(
        source.get(AZURE_OPENAI_API_KEY_ENV) and source.get(AZURE_OPENAI_ENDPOINT_ENV)
    )
    deployment = source.get(AZURE_OPENAI_DEPLOYMENT_NAME_ENV)

    google_api_key = source.get(GOOGLE_API_KEY_ENV)
    gemini_model = source.get(GEMINI_MODEL_ENV)
    use_gemini_for_experts = bool(google_api_key and gemini_model)

    model_map = default_model_map(
        provider="azure" if use_azure else "openai",
        deployment=deployment if use_azure else None,
        expert_provider="google" if use_gemini_for_experts else None,
        expert_model=gemini_model if use_gemini_for_experts else None,
    )

    if model_overrides:
        model_map.update(model_overrides)

    return AppConfig(
        openai_api_key=source.get(OPENAI_API_KEY_ENV),
        azure_openai_api_key=source.get(AZURE_OPENAI_API_KEY_ENV),
        azure_openai_endpoint=source.get(AZURE_OPENAI_ENDPOINT_ENV),
        azure_openai_deployment_name=deployment,
        google_api_key=google_api_key,
        gemini_model=gemini_model,
        tavily_api_key=source.get(TAVILY_API_KEY_ENV),
        brave_api_key=source.get(BRAVE_API_KEY_ENV),
        firecrawl_api_key=source.get(FIRECRAWL_API_KEY_ENV),
        filesystem=FilesystemConfig(base_path=fs_base),
        model_map=model_map,
    )


def create_chat_model(model_config: ModelConfig, app_config: AppConfig) -> Any:
    """
    Create a LangChain ChatModel instance from configuration.

    Returns a ChatOpenAI, AzureChatOpenAI, or ChatGoogleGenerativeAI instance
    depending on the provider specified in model_config.
    """
    if model_config.provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            model=model_config.model,
            azure_endpoint=app_config.azure_openai_endpoint,
            api_key=app_config.azure_openai_api_key,
            azure_deployment=model_config.deployment,
            api_version="2025-04-01-preview",
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

    if model_config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_config.model,
            google_api_key=app_config.google_api_key,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_config.model,
        api_key=app_config.openai_api_key,
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
    )


__all__ = [
    "AppConfig",
    "FilesystemConfig",
    "ModelConfig",
    "default_model_map",
    "load_settings",
    "create_chat_model",
    "OPENAI_API_KEY_ENV",
    "AZURE_OPENAI_API_KEY_ENV",
    "AZURE_OPENAI_ENDPOINT_ENV",
    "AZURE_OPENAI_DEPLOYMENT_NAME_ENV",
    "GOOGLE_API_KEY_ENV",
    "GEMINI_MODEL_ENV",
    "TAVILY_API_KEY_ENV",
    "BRAVE_API_KEY_ENV",
    "FIRECRAWL_API_KEY_ENV",
    "FILESYSTEM_BASE_ENV",
]
