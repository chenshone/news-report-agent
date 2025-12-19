"""Pytest configuration and fixtures."""

import os

import pytest
from dotenv import load_dotenv

# Load .env file at the start of test session
load_dotenv()


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require external APIs",
    )


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to set up mock environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    return monkeypatch


def has_api_key(key_name: str) -> bool:
    """Check if an API key is available in environment."""
    value = os.getenv(key_name)
    return value is not None and len(value) > 0 and not value.startswith("YOUR_")


@pytest.fixture
def skip_if_no_api_key():
    """
    Fixture that skips the test if required API keys are not configured.
    
    Checks for:
    - OPENAI_API_KEY or complete Azure OpenAI configuration
    - TAVILY_API_KEY
    """
    # Check for OpenAI
    has_openai = has_api_key("OPENAI_API_KEY")
    
    # Check for Azure OpenAI (need all required fields)
    has_azure = (
        has_api_key("AZURE_OPENAI_API_KEY")
        and has_api_key("AZURE_OPENAI_ENDPOINT")
        and has_api_key("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    
    # Need at least one LLM provider
    if not has_openai and not has_azure:
        pytest.skip(
            "No valid LLM API key configured. "
            "Set OPENAI_API_KEY or complete Azure OpenAI configuration in .env"
        )
    
    # Check for Tavily (required for tools)
    if not has_api_key("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY not configured in .env")
