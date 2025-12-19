"""Web scraping tool for fetching article content."""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool


@tool
def fetch_page(url: str, max_length: int = 5000) -> str:
    """
    Fetch and extract the main text content from a web page.
    
    This tool retrieves a web page and extracts its main textual content,
    removing ads, navigation, and other non-essential elements. It's optimized
    for news articles and blog posts.
    
    Args:
        url: The URL of the page to fetch
        max_length: Maximum length of content to return in characters (default: 5000)
        
    Returns:
        The extracted main text content, truncated to max_length if necessary.
        Returns an error message string if fetching fails.
        
    Examples:
        >>> content = fetch_page("https://example.com/article")
        >>> print(len(content))
        4523
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: Required libraries not installed. Please install httpx and beautifulsoup4."
    
    try:
        # Use httpx with reasonable timeout
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
        # Parse HTML
        soup = BeautifulSoup(response.text, "lxml")
        
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", 
                            "aside", "iframe", "noscript"]):
            element.decompose()
        
        # Try to find main content area
        main_content = None
        
        # Common content containers (priority order)
        content_selectors = [
            "article",
            '[role="main"]',
            "main",
            ".article-content",
            ".post-content",
            ".entry-content",
            "#content",
            ".content",
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Fallback to body if no main content found
        if not main_content:
            main_content = soup.find("body")
        
        if not main_content:
            return "Error: Could not extract content from page"
        
        # Extract text
        text = main_content.get_text(separator="\n", strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        # Truncate if necessary
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
        
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {url}"
    except httpx.RequestError as e:
        return f"Error: Network request failed - {str(e)}"
    except Exception as e:
        return f"Error: {type(e).__name__} - {str(e)}"


@tool
async def fetch_page_async(url: str, max_length: int = 5000) -> str:
    """
    Async version of fetch_page for better performance.
    
    Same as fetch_page but uses async HTTP client for concurrent fetching.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: Required libraries not installed. Please install httpx and beautifulsoup4."
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
        # Parse HTML (BeautifulSoup is sync, but it's fast enough)
        soup = BeautifulSoup(response.text, "lxml")
        
        # Remove non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", 
                            "aside", "iframe", "noscript"]):
            element.decompose()
        
        # Try to find main content
        main_content = None
        content_selectors = [
            "article",
            '[role="main"]',
            "main",
            ".article-content",
            ".post-content",
            ".entry-content",
            "#content",
            ".content",
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.find("body")
        
        if not main_content:
            return "Error: Could not extract content from page"
        
        # Extract and clean text
        text = main_content.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        # Truncate if necessary
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
        
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {url}"
    except httpx.RequestError as e:
        return f"Error: Network request failed - {str(e)}"
    except Exception as e:
        return f"Error: {type(e).__name__} - {str(e)}"


__all__ = ["fetch_page", "fetch_page_async"]

