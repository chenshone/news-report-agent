from datetime import datetime

from src.schemas import (
    AnalysisResult,
    IntegratedSummary,
    NewsItem,
    ScoreBreakdown,
)


def test_news_item_round_trip():
    timestamp = datetime(2024, 5, 1, 12, 0, 0)
    grades = ScoreBreakdown(credibility="A", relevance="B")
    item = NewsItem(
        id="1",
        title="AI breaks new ground",
        url="https://example.com/ai",
        source="Example News",
        summary="Summary text",
        content="Full content",
        published_at=timestamp,
        grades=grades,
        tags=["ai", "innovation"],
        metadata={"region": "global"},
    )

    payload = item.to_dict()
    restored = NewsItem.from_dict(payload)

    assert payload["published_at"] == timestamp.isoformat()
    assert restored.published_at == timestamp
    assert restored.grades.credibility == "A"
    assert restored.tags == ["ai", "innovation"]
    assert restored.metadata["region"] == "global"


def test_analysis_result_round_trip():
    result = AnalysisResult(
        news_id="1",
        expert_role="summarizer",
        analysis="Key points",
        confidence_grade="B",
        references=["https://example.com/ref"],
        metadata={"note": "checked"},
    )

    payload = result.to_dict()
    restored = AnalysisResult.from_dict(payload)

    assert restored.expert_role == "summarizer"
    assert restored.confidence_grade == "B"
    assert restored.references == ["https://example.com/ref"]
    assert restored.metadata["note"] == "checked"


def test_integrated_summary_round_trip():
    summary = IntegratedSummary(
        article_id="1",
        title="Daily report",
        integrated_analysis="Full integrated analysis",
        references=["https://example.com/a", "https://example.com/b"],
        highlights=["point A", "point B"],
        metadata={"score": 1},
    )

    payload = summary.to_dict()
    restored = IntegratedSummary.from_dict(payload)

    assert restored.title == "Daily report"
    assert restored.highlights == ["point A", "point B"]
    assert len(restored.references) == 2
    assert restored.metadata["score"] == 1


def test_score_breakdown_default_from_dict():
    scores = ScoreBreakdown.from_dict(None)

    assert scores.credibility is None
    assert scores.relevance is None
    assert scores.quality is None
