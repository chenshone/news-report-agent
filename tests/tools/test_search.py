"""Tests for internet search tool."""

import os

import pytest

from src.tools.search import internet_search


def test_internet_search_no_tavily():
    """Test that search returns error when Tavily is not configured."""
    # This test runs without actual API key
    result = internet_search.invoke({
        "query": "test query",
        "max_results": 3,
    })
    
    assert isinstance(result, list)
    assert len(result) >= 1
    
    # Without API key, should return error message
    first_result = result[0]
    assert "title" in first_result
    assert "url" in first_result
    assert "content" in first_result


def test_internet_search_limits_max_results():
    """Test that max_results is properly bounded."""
    # Even with large max_results request, should be capped
    result = internet_search.invoke({
        "query": "AI news",
        "max_results": 100,  # Very large number
    })
    
    assert isinstance(result, list)
    # Should be limited (either by our cap or by error)
    assert len(result) <= 10


def test_internet_search_integration():
    """Integration test with real Tavily API (requires API key)."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    # Skip if no API key or if it's the placeholder
    if not tavily_key or tavily_key.startswith("YOUR_"):
        pytest.skip("TAVILY_API_KEY not configured in .env")
    
    result = internet_search.invoke({
        "query": "artificial intelligence news 2024",
        "max_results": 3,
    })
    
    assert isinstance(result, list)
    assert len(result) > 0
    
    # Check structure of results
    for item in result:
        assert "title" in item
        assert "url" in item
        assert "content" in item
        assert "source" in item
        assert "score" in item
        
        # Basic validation
        if not item["title"].startswith("Error"):
            assert len(item["title"]) > 0
            assert item["url"].startswith("http")
            assert isinstance(item["score"], (int, float))


def test_internet_search_with_topic():
    """Test search with topic parameter."""
    result = internet_search.invoke({
        "query": "latest tech developments",
        "max_results": 2,
        "topic": "news",
    })
    
    assert isinstance(result, list)
    assert len(result) >= 1

