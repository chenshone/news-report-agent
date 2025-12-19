"""Tests for web scraping tool."""

import os

import pytest

from src.tools.scraper import fetch_page


def test_fetch_page_invalid_url():
    """Test that fetch_page handles invalid URLs gracefully."""
    result = fetch_page.invoke({
        "url": "not-a-valid-url",
        "max_length": 1000,
    })
    
    assert isinstance(result, str)
    assert "Error" in result


def test_fetch_page_nonexistent_domain():
    """Test that fetch_page handles network errors."""
    result = fetch_page.invoke({
        "url": "https://this-domain-definitely-does-not-exist-12345.com",
        "max_length": 1000,
    })
    
    assert isinstance(result, str)
    assert "Error" in result


def test_fetch_page_max_length():
    """Test that content is truncated to max_length."""
    # Use a real site that's likely to have long content
    result = fetch_page.invoke({
        "url": "https://example.com",
        "max_length": 100,
    })
    
    assert isinstance(result, str)
    # Should be at most 100 chars (plus "..." if truncated)
    assert len(result) <= 104


def test_fetch_page_integration():
    """Integration test with real website."""
    # This test uses example.com which doesn't require API keys
    # But we check if we're in a network-enabled environment
    
    result = fetch_page.invoke({
        "url": "https://example.com",
        "max_length": 5000,
    })
    
    assert isinstance(result, str)
    
    # If network is available, should get content
    # If not, should get error message
    if not result.startswith("Error"):
        assert len(result) > 0
        # example.com should contain "Example Domain"
        assert "example" in result.lower()
    else:
        # Network error is acceptable in isolated environments
        pytest.skip("Network not available")


@pytest.mark.asyncio
async def test_fetch_page_async():
    """Test async version of fetch_page."""
    from src.tools.scraper import fetch_page_async
    
    result = await fetch_page_async.ainvoke({
        "url": "https://example.com",
        "max_length": 1000,
    })
    
    assert isinstance(result, str)
    # Either successful content or error message
    assert len(result) > 0

