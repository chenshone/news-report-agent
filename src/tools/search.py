"""Internet search tool using Tavily API."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool


@tool
def internet_search(
    query: str,
    max_results: int = 8,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search the internet for relevant news and information.
    
    This tool uses the Tavily API to search for high-quality, recent content
    related to the given query. It's optimized for news and current events.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 8, max: 10)
                     建议设置为 8-10 以获取足够的候选内容
        topic: Optional topic hint for better results (e.g., "news", "general")
        
    Returns:
        A list of search results, each containing:
        - title: Article title
        - url: Article URL
        - content: Snippet or summary of the content
        - source: Domain name of the source
        - published_date: Publication date if available (ISO format string)
        - score: Relevance score from the search engine
        
    Examples:
        >>> results = internet_search("AI Agent 最新进展", max_results=3)
        >>> print(results[0]["title"])
        "DeepMind releases new AI agent framework"
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        return [
            {
                "title": "Error: Tavily not installed",
                "url": "",
                "content": "Please install tavily-python: pip install tavily-python",
                "source": "error",
                "score": 0.0,
            }
        ]
    
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [
            {
                "title": "Error: TAVILY_API_KEY not set",
                "url": "",
                "content": "Please set TAVILY_API_KEY environment variable",
                "source": "error",
                "score": 0.0,
            }
        ]
    
    # Limit max_results to reasonable range
    max_results = min(max(1, max_results), 10)
    
    try:
        client = TavilyClient(api_key=api_key)
        
        # Tavily search parameters
        search_params: Dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",  # More thorough search
            "include_raw_content": False,  # We'll fetch full content separately if needed
        }
        
        # Add topic if specified
        if topic:
            search_params["topic"] = topic
        
        response = client.search(**search_params)
        
        # Transform Tavily response to our standard format
        results = []
        for item in response.get("results", []):
            result = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "source": item.get("url", "").split("/")[2] if item.get("url") else "",
                "score": item.get("score", 0.0),
            }
            
            # Add published date if available
            if "published_date" in item:
                result["published_date"] = item["published_date"]
            
            results.append(result)
        
        return results
        
    except Exception as e:
        # Return error as result to avoid breaking the agent flow
        return [
            {
                "title": f"Search error: {type(e).__name__}",
                "url": "",
                "content": str(e),
                "source": "error",
                "score": 0.0,
            }
        ]


# Async version for better performance in agent workflows
@tool
async def internet_search_async(
    query: str,
    max_results: int = 5,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Async version of internet_search.
    
    Same as internet_search but runs asynchronously for better performance
    in async agent workflows.
    """
    # For now, Tavily doesn't have official async client
    # We'll wrap the sync version
    import asyncio
    
    return await asyncio.to_thread(internet_search.invoke, {
        "query": query,
        "max_results": max_results,
        "topic": topic,
    })


__all__ = ["internet_search", "internet_search_async"]

