"""Content evaluation tools for credibility and relevance assessment.

Grade system (A/B/C/D):
- A: Excellent - High quality, can use directly
- B: Good - Good quality, minor issues acceptable
- C: Fair - Obvious issues, needs improvement
- D: Poor - Serious issues, needs redo
"""

from __future__ import annotations

import re
from typing import Any, Literal
from urllib.parse import urlparse

from langchain_core.tools import tool

GradeType = Literal["A", "B", "C", "D"]

TRUSTED_DOMAINS = {
    # International news
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "cnn.com",
    "nytimes.com", "washingtonpost.com", "theguardian.com", "wsj.com",
    "bloomberg.com", "ft.com", "economist.com",
    # Tech news
    "techcrunch.com", "theverge.com", "arstechnica.com", "wired.com",
    "technologyreview.com", "spectrum.ieee.org",
    # Chinese news
    "xinhuanet.com", "people.com.cn", "chinadaily.com.cn",
    "caixin.com", "36kr.com", "ifeng.com",
    # Academic/Research
    "nature.com", "science.org", "arxiv.org", "acm.org",
    # Official sources
    "gov.cn", "gov", "edu.cn", "edu",
}

SUSPICIOUS_DOMAINS = {
    "buzzfeed.com", "upworthy.com", "viralthread.com",
    "taboola.com", "outbrain.com",
}

CLICKBAIT_PATTERNS = [
    r"震惊", r"惊呆", r"吓尿", r"不敢相信", r"竟然", r"居然",
    r"必看", r"速看", r"必转", r"火爆", r"刷屏",
    r"太牛了", r"绝了", r"疯了", r"炸了",
    r"你绝对想不到", r"真相令人", r"内幕曝光",
    r"you won't believe", r"shocking", r"one weird trick",
    r"doctors hate", r"this will blow your mind",
    r"what happened next", r"number \d+ will shock you",
]

DOMAIN_KEYWORDS = {
    "科技": ["科技", "技术", "tech", "technology", "数字化", "创新", "innovation"],
    "ai": [
        "ai", "人工智能", "artificial intelligence", "机器学习", "machine learning",
        "深度学习", "deep learning", "神经网络", "neural network", "大模型", "llm",
        "gpt", "chatgpt", "claude", "agent",
    ],
    "财经": [
        "财经", "金融", "经济", "finance", "economy", "股市", "股票", "投资",
        "银行", "基金", "债券", "货币",
    ],
    "政治": ["政治", "政府", "政策", "politics", "policy", "government", "法律", "立法"],
    "娱乐": ["娱乐", "影视", "电影", "音乐", "明星", "entertainment", "celebrity"],
    "体育": ["体育", "运动", "sports", "比赛", "足球", "篮球", "奥运"],
    "健康": ["健康", "医疗", "health", "医学", "疾病", "治疗", "药物"],
}

GRADE_THRESHOLDS = [(0.7, "A"), (0.5, "B"), (0.3, "C")]


def _score_to_grade(score: float) -> GradeType:
    """Convert internal score to grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade  # type: ignore[return-value]
    return "D"


def _check_domain_reputation(domain: str) -> tuple[str, float]:
    """Check if domain is trusted or suspicious."""
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith(f".{trusted}"):
            return "trusted", 0.3

    for suspicious in SUSPICIOUS_DOMAINS:
        if domain == suspicious or domain.endswith(f".{suspicious}"):
            return "suspicious", -0.3

    return "unknown", 0.0


@tool
def evaluate_credibility(url: str, title: str) -> dict[str, Any]:
    """
    Evaluate the credibility of a news source based on domain and title.

    Analyzes domain reputation, title quality, and URL structure.

    Args:
        url: The URL of the article.
        title: The article title.

    Returns:
        A dictionary with grade (A/B/C/D), reasons, flags, and domain_category.
    """
    score = 0.5
    reasons: list[str] = []
    flags: list[str] = []

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return {
                "grade": "D",
                "reasons": ["Invalid URL format - no domain found"],
                "flags": ["URL_PARSE_ERROR"],
                "domain_category": "unknown",
            }
        if domain.startswith("www."):
            domain = domain[4:]
    except Exception:
        return {
            "grade": "D",
            "reasons": ["Invalid URL format"],
            "flags": ["URL_PARSE_ERROR"],
            "domain_category": "unknown",
        }

    # Domain reputation
    domain_category, domain_score = _check_domain_reputation(domain)
    score += domain_score
    if domain_category == "trusted":
        reasons.append(f"来自可信来源: {domain}")
    elif domain_category == "suspicious":
        reasons.append(f"来自可疑来源: {domain}")
        flags.append("SUSPICIOUS_DOMAIN")

    # URL patterns
    if re.search(r"\d{8,}", url):
        score -= 0.1
        flags.append("SUSPICIOUS_URL_PATTERN")

    # Clickbait detection
    clickbait_count = sum(1 for p in CLICKBAIT_PATTERNS if re.search(p, title, re.IGNORECASE))
    if clickbait_count > 0:
        score -= min(0.3, clickbait_count * 0.1)
        reasons.append(f"标题包含 {clickbait_count} 个诱导性词汇")
        flags.append("CLICKBAIT_TITLE")

    # Title length
    title_len = len(title)
    if title_len < 10:
        score -= 0.1
        flags.append("TITLE_TOO_SHORT")
    elif title_len > 200:
        score -= 0.1
        flags.append("TITLE_TOO_LONG")

    # Excessive punctuation
    punct_ratio = sum(1 for c in title if c in "!?。！？") / max(len(title), 1)
    if punct_ratio > 0.15:
        score -= 0.15
        reasons.append("标题包含过多感叹号或问号")
        flags.append("EXCESSIVE_PUNCTUATION")

    # Positive indicators
    if url.startswith("https://"):
        score += 0.05
        reasons.append("使用安全连接 (HTTPS)")

    if re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", title):
        score += 0.05
        reasons.append("标题包含日期信息")

    score = max(0.0, min(1.0, score))
    grade = _score_to_grade(score)

    grade_descriptions = {
        "A": "可信度高，来源可靠",
        "B": "可信度良好，基本可信",
        "C": "可信度一般，需要核实",
        "D": "可信度低，谨慎对待",
    }
    reasons.insert(0, grade_descriptions[grade])

    return {
        "grade": grade,
        "reasons": reasons,
        "flags": flags,
        "domain_category": domain_category,
    }


@tool
def evaluate_relevance(
    content: str, domain: str, query: str | None = None
) -> dict[str, Any]:
    """
    Evaluate the relevance of content to a given domain or query.

    Provides a heuristic assessment of whether content matches the topic.

    Args:
        content: The content to evaluate (title + snippet or full text).
        domain: The target domain/topic (e.g., "科技", "AI", "财经").
        query: Optional specific query for more precise matching.

    Returns:
        A dictionary with grade (A/B/C/D), reasons, and matched_keywords.
    """
    score = 0.0
    reasons: list[str] = []
    matched_keywords: list[str] = []

    content_lower = content.lower()
    target_keywords = DOMAIN_KEYWORDS.get(domain.lower(), [domain.lower()])

    for keyword in target_keywords:
        if keyword in content_lower:
            score += 0.15
            matched_keywords.append(keyword)

    if len(matched_keywords) > 2:
        score += 0.1
        reasons.append(f"包含多个相关关键词 ({len(matched_keywords)}个)")

    if query:
        query_terms = query.lower().split()
        query_matches = sum(1 for term in query_terms if len(term) > 2 and term in content_lower)
        if query_matches > 0:
            score += min(0.3, query_matches * 0.1)
            reasons.append(f"匹配查询词 {query_matches} 个")

    content_len = len(content)
    if content_len < 50:
        score -= 0.1
        reasons.append("内容过短")
    elif content_len > 200:
        score += 0.05
        reasons.append("内容充实")

    score = max(0.0, min(1.0, score))
    grade = _score_to_grade(score)

    grade_descriptions = {
        "A": "内容高度相关",
        "B": "内容较为相关",
        "C": "内容部分相关",
        "D": "内容相关性较低",
    }
    reasons.insert(0, grade_descriptions[grade])

    return {
        "grade": grade,
        "reasons": reasons,
        "matched_keywords": matched_keywords,
    }


__all__ = ["evaluate_credibility", "evaluate_relevance"]
