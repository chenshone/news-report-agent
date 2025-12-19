"""Content evaluation tools for credibility and relevance assessment.

评估结果使用 A/B/C/D 四级制：
- A: 优秀 - 质量高，可直接采用
- B: 良好 - 质量较好，小问题不影响整体
- C: 及格 - 有明显问题，需改进
- D: 不及格 - 严重问题，需重做
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

from langchain_core.tools import tool

from ..schemas import Grade

# 等级类型
GradeType = Literal["A", "B", "C", "D"]


def _score_to_grade(score: float) -> GradeType:
    """内部分数转换为等级（仅用于计算过程）"""
    if score >= 0.7:
        return "A"
    elif score >= 0.5:
        return "B"
    elif score >= 0.3:
        return "C"
    else:
        return "D"


# Domain reputation lists
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
    # Content farms and low-quality sites
    "buzzfeed.com", "upworthy.com", "viralthread.com",
    # Known for clickbait
    "taboola.com", "outbrain.com",
}

# Clickbait/sensational keywords (Chinese and English)
CLICKBAIT_PATTERNS = [
    # Chinese clickbait
    r"震惊", r"惊呆", r"吓尿", r"不敢相信", r"竟然", r"居然",
    r"必看", r"速看", r"必转", r"火爆", r"刷屏",
    r"太牛了", r"绝了", r"疯了", r"炸了",
    r"你绝对想不到", r"真相令人", r"内幕曝光",
    # English clickbait
    r"you won't believe", r"shocking", r"one weird trick",
    r"doctors hate", r"this will blow your mind",
    r"what happened next", r"number \d+ will shock you",
]


@tool
def evaluate_credibility(url: str, title: str) -> Dict[str, any]:
    """
    Evaluate the credibility of a news source based on domain and title.
    
    This tool performs a quick credibility check by analyzing:
    1. Domain reputation (trusted/suspicious/unknown)
    2. Title quality (clickbait detection)
    3. URL structure (suspicious patterns)
    
    Args:
        url: The URL of the article
        title: The article title
        
    Returns:
        A dictionary containing:
        - grade: Credibility grade (A/B/C/D)
        - reasons: List of reasons for the grade
        - flags: List of warning flags if any
        - domain_category: "trusted" / "suspicious" / "unknown"
        
    Examples:
        >>> result = evaluate_credibility("https://reuters.com/tech/ai-breakthrough", "AI研究新突破")
        >>> print(result["grade"])
        A
    """
    # 内部使用分数计算，最后转换为等级
    _score = 0.5  # Start with neutral score
    reasons: List[str] = []
    flags: List[str] = []
    
    # Parse domain
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check if URL is valid (has domain)
        if not domain:
            return {
                "grade": "D",
                "reasons": ["Invalid URL format - no domain found"],
                "flags": ["URL_PARSE_ERROR"],
                "domain_category": "unknown",
            }
        
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
            
    except Exception:
        return {
            "grade": "D",
            "reasons": ["Invalid URL format"],
            "flags": ["URL_PARSE_ERROR"],
            "domain_category": "unknown",
        }
    
    # 1. Domain reputation check
    domain_category = "unknown"
    
    # Check if domain or its parent is in trusted list
    is_trusted = False
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith(f".{trusted}"):
            is_trusted = True
            break
    
    if is_trusted:
        _score += 0.3
        reasons.append(f"来自可信来源: {domain}")
        domain_category = "trusted"
    
    # Check if domain is suspicious
    is_suspicious = False
    for suspicious in SUSPICIOUS_DOMAINS:
        if domain == suspicious or domain.endswith(f".{suspicious}"):
            is_suspicious = True
            break
    
    if is_suspicious:
        _score -= 0.3
        reasons.append(f"来自可疑来源: {domain}")
        flags.append("SUSPICIOUS_DOMAIN")
        domain_category = "suspicious"
    
    # Check for suspicious URL patterns
    if any(pattern in url.lower() for pattern in ["?ref=", "?utm_source=", "?click_id="]):
        # These are just tracking params, not necessarily bad
        pass
    
    if re.search(r"\d{8,}", url):  # Long number sequences (often in low-quality sites)
        _score -= 0.1
        flags.append("SUSPICIOUS_URL_PATTERN")
    
    # 2. Title quality check
    title_lower = title.lower()
    
    # Check for clickbait patterns
    clickbait_count = 0
    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            clickbait_count += 1
    
    if clickbait_count > 0:
        penalty = min(0.3, clickbait_count * 0.1)
        _score -= penalty
        reasons.append(f"标题包含 {clickbait_count} 个诱导性词汇")
        flags.append("CLICKBAIT_TITLE")
    
    # Check title length (too short or too long can be suspicious)
    title_len = len(title)
    if title_len < 10:
        _score -= 0.1
        flags.append("TITLE_TOO_SHORT")
    elif title_len > 200:
        _score -= 0.1
        flags.append("TITLE_TOO_LONG")
    
    # Check for excessive punctuation
    punct_ratio = sum(1 for c in title if c in "!?。！？") / max(len(title), 1)
    if punct_ratio > 0.15:
        _score -= 0.15
        reasons.append("标题包含过多感叹号或问号")
        flags.append("EXCESSIVE_PUNCTUATION")
    
    # 3. Positive indicators
    # Has HTTPS (basic security)
    if url.startswith("https://"):
        _score += 0.05
        reasons.append("使用安全连接 (HTTPS)")
    
    # Professional title style (contains date or author indicators)
    if re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", title):
        _score += 0.05
        reasons.append("标题包含日期信息")
    
    # Ensure score is within [0, 1]
    _score = max(0.0, min(1.0, _score))
    
    # 转换为等级
    grade = _score_to_grade(_score)
    
    # Add overall assessment based on grade
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
def evaluate_relevance(content: str, domain: str, query: Optional[str] = None) -> Dict[str, any]:
    """
    Evaluate the relevance of content to a given domain or query.
    
    This tool provides a quick heuristic assessment of whether content
    matches the expected domain/topic. It's useful for filtering search
    results before deeper LLM-based analysis.
    
    Args:
        content: The content to evaluate (title + snippet or full text)
        domain: The target domain/topic (e.g., "科技", "AI", "财经")
        query: Optional specific query for more precise matching
        
    Returns:
        A dictionary containing:
        - grade: Relevance grade (A/B/C/D)
        - reasons: List of reasons for the grade
        - matched_keywords: Keywords that matched
        
    Examples:
        >>> result = evaluate_relevance("GPT-4的最新进展...", "AI")
        >>> print(result["grade"])
        A
    """
    # 内部使用分数计算，最后转换为等级
    _score = 0.0
    reasons: List[str] = []
    matched_keywords: List[str] = []
    
    content_lower = content.lower()
    
    # Domain keyword mappings
    domain_keywords = {
        "科技": ["科技", "技术", "tech", "technology", "数字化", "创新", "innovation"],
        "ai": ["ai", "人工智能", "artificial intelligence", "机器学习", "machine learning",
               "深度学习", "deep learning", "神经网络", "neural network", "大模型", "llm",
               "gpt", "chatgpt", "claude", "agent"],
        "财经": ["财经", "金融", "经济", "finance", "economy", "股市", "股票", "投资",
                "银行", "基金", "债券", "货币"],
        "政治": ["政治", "政府", "政策", "politics", "policy", "government", "法律", "立法"],
        "娱乐": ["娱乐", "影视", "电影", "音乐", "明星", "entertainment", "celebrity"],
        "体育": ["体育", "运动", "sports", "比赛", "足球", "篮球", "奥运"],
        "健康": ["健康", "医疗", "health", "医学", "疾病", "治疗", "药物"],
    }
    
    # Get keywords for the specified domain
    target_keywords = domain_keywords.get(domain.lower(), [])
    
    # If no predefined keywords, use the domain itself
    if not target_keywords:
        target_keywords = [domain.lower()]
    
    # Count keyword matches
    for keyword in target_keywords:
        if keyword in content_lower:
            _score += 0.15
            matched_keywords.append(keyword)
    
    # Bonus for multiple matches
    if len(matched_keywords) > 2:
        _score += 0.1
        reasons.append(f"包含多个相关关键词 ({len(matched_keywords)}个)")
    
    # If query is provided, check query terms
    if query:
        query_terms = query.lower().split()
        query_matches = sum(1 for term in query_terms if len(term) > 2 and term in content_lower)
        
        if query_matches > 0:
            query_score = min(0.3, query_matches * 0.1)
            _score += query_score
            reasons.append(f"匹配查询词 {query_matches} 个")
    
    # Content length check (too short might be irrelevant snippet)
    content_len = len(content)
    if content_len < 50:
        _score -= 0.1
        reasons.append("内容过短")
    elif content_len > 200:
        _score += 0.05
        reasons.append("内容充实")
    
    # Ensure score is within [0, 1]
    _score = max(0.0, min(1.0, _score))
    
    # 转换为等级
    grade = _score_to_grade(_score)
    
    # Overall assessment based on grade
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

