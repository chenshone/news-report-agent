"""Base classes and common utilities for information sources."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceResult(BaseModel):
    """Unified result format for all information sources."""

    title: str = Field(..., description="Title of the content")
    url: str = Field(..., description="URL to the content")
    content: str = Field(..., description="Content snippet or summary")
    source_type: str = Field(..., description="Source type (arxiv, github, hackernews, rss)")
    source_name: str = Field(..., description="Specific source name")
    published_date: Optional[str] = Field(None, description="Publication date if available")
    score: float = Field(0.0, description="Relevance score if available")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


def build_error_result(source_type: str, title: str, content: str) -> list[dict[str, Any]]:
    """Build a standardized error result."""
    return [
        {
            "title": title,
            "url": "",
            "content": content,
            "source_type": source_type,
            "source_name": "error",
            "score": 0.0,
        }
    ]
