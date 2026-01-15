"""arXiv search tool for academic papers.

Uses the arXiv API to search for recent research papers.
No API key required - fully free.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from .base import build_error_result


def _format_arxiv_result(entry: Any) -> dict[str, Any]:
    """Format a single arXiv entry to our standard format."""
    # Extract authors (limit to first 5)
    authors = [author.name for author in entry.authors[:5]]
    if len(entry.authors) > 5:
        authors.append(f"... and {len(entry.authors) - 5} more")

    # Get primary category
    primary_category = entry.primary_category if hasattr(entry, "primary_category") else ""

    # Format published date
    published = entry.published.strftime("%Y-%m-%d") if entry.published else ""

    return {
        "title": entry.title.replace("\n", " "),
        "url": entry.entry_id,
        "content": entry.summary.replace("\n", " ")[:500] + "..."
        if len(entry.summary) > 500
        else entry.summary.replace("\n", " "),
        "source_type": "arxiv",
        "source_name": "arXiv",
        "published_date": published,
        "score": 1.0,  # arXiv doesn't provide relevance scores
        "metadata": {
            "arxiv_id": entry.entry_id.split("/")[-1],
            "authors": authors,
            "primary_category": primary_category,
            "pdf_url": entry.pdf_url,
            "categories": [cat.term for cat in entry.categories] if entry.categories else [],
        },
    }


@tool
def search_arxiv(
    query: str,
    max_results: int = 10,
    categories: list[str] | None = None,
    days_back: int = 30,
) -> list[dict[str, Any]]:
    """
    Search arXiv for recent academic papers and research.

    Use this tool to find cutting-edge research, technical papers, and academic developments.
    Best for: AI/ML papers, scientific discoveries, technical innovations.

    Args:
        query: Search query (e.g., "large language models", "AI agents").
        max_results: Maximum number of papers to return (default: 10, max: 50).
        categories: Optional list of arXiv categories to filter by
                    (e.g., ["cs.AI", "cs.LG", "cs.CL"]).
        days_back: Only return papers from the last N days (default: 30).

    Returns:
        List of papers with title, abstract, authors, arXiv ID, and PDF link.

    Example categories:
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - cs.CL: Computation and Language (NLP)
        - cs.CV: Computer Vision
        - cs.RO: Robotics
    """
    try:
        import arxiv
    except ImportError:
        return build_error_result(
            "arxiv",
            "Error: arxiv not installed",
            "Please install arxiv: pip install arxiv",
        )

    max_results = min(max(1, max_results), 50)

    try:
        # Build search query
        search_query = query

        # Add category filter if specified
        if categories:
            cat_filter = " OR ".join([f"cat:{cat}" for cat in categories])
            search_query = f"({query}) AND ({cat_filter})"

        # Create search client
        client = arxiv.Client()
        search = arxiv.Search(
            query=search_query,
            max_results=max_results * 2,  # Fetch extra to filter by date
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        # Calculate date cutoff
        cutoff_date = datetime.now() - timedelta(days=days_back)

        results = []
        for entry in client.results(search):
            # Filter by date
            if entry.published and entry.published.replace(tzinfo=None) >= cutoff_date:
                results.append(_format_arxiv_result(entry))
                if len(results) >= max_results:
                    break

        if not results:
            return [
                {
                    "title": f"No recent papers found for: {query}",
                    "url": "",
                    "content": f"No arXiv papers matching '{query}' were published in the last {days_back} days. "
                    "Try expanding the time range or using different keywords.",
                    "source_type": "arxiv",
                    "source_name": "arXiv",
                    "score": 0.0,
                }
            ]

        return results

    except Exception as e:
        return build_error_result("arxiv", f"arXiv search error: {type(e).__name__}", str(e))


__all__ = ["search_arxiv"]
