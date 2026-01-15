"""Web scraping tool for fetching article content."""

from __future__ import annotations

from langchain_core.tools import tool

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_CONTENT_SELECTORS = [
    "article",
    '[role="main"]',
    "main",
    ".article-content",
    ".post-content",
    ".entry-content",
    "#content",
    ".content",
]

_NON_CONTENT_TAGS = ["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]


def _extract_content(html: str, max_length: int) -> str:
    """Extract main text content from HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    for element in soup(_NON_CONTENT_TAGS):
        element.decompose()

    main_content = None
    for selector in _CONTENT_SELECTORS:
        main_content = soup.select_one(selector)
        if main_content:
            break

    if not main_content:
        main_content = soup.find("body")

    if not main_content:
        return "Error: Could not extract content from page"

    text = main_content.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


@tool
def fetch_page(url: str, max_length: int = 5000) -> str:
    """
    Fetch and extract the main text content from a web page.

    Retrieves a web page and extracts its main textual content,
    removing ads, navigation, and other non-essential elements.

    Args:
        url: The URL of the page to fetch.
        max_length: Maximum content length in characters (default: 5000).

    Returns:
        The extracted main text content, or an error message string.
    """
    try:
        import httpx
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError:
        return "Error: Required libraries not installed. Please install httpx and beautifulsoup4."

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=_DEFAULT_HEADERS)
            response.raise_for_status()

        return _extract_content(response.text, max_length)

    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {url}"
    except httpx.RequestError as e:
        return f"Error: Network request failed - {e}"
    except Exception as e:
        return f"Error: {type(e).__name__} - {e}"


@tool
async def fetch_page_async(url: str, max_length: int = 5000) -> str:
    """Async version of fetch_page for concurrent fetching."""
    try:
        import httpx
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError:
        return "Error: Required libraries not installed. Please install httpx and beautifulsoup4."

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=_DEFAULT_HEADERS)
            response.raise_for_status()

        return _extract_content(response.text, max_length)

    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {url}"
    except httpx.RequestError as e:
        return f"Error: Network request failed - {e}"
    except Exception as e:
        return f"Error: {type(e).__name__} - {e}"


__all__ = ["fetch_page", "fetch_page_async"]
