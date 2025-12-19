"""Tests for content evaluation tools."""

import pytest

from src.tools.evaluator import evaluate_credibility, evaluate_relevance


class TestEvaluateCredibility:
    """Tests for evaluate_credibility tool."""
    
    def test_trusted_domain(self):
        """Test that trusted domains get high scores."""
        result = evaluate_credibility.invoke({
            "url": "https://reuters.com/technology/ai-breakthrough-2024",
            "title": "New AI Breakthrough Announced",
        })
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "reasons" in result
        assert "domain_category" in result
        
        assert result["score"] >= 0.7
        assert result["domain_category"] == "trusted"
    
    def test_suspicious_domain(self):
        """Test that suspicious domains get low scores."""
        result = evaluate_credibility.invoke({
            "url": "https://buzzfeed.com/some-article",
            "title": "Normal Title",
        })
        
        assert result["score"] < 0.5
        assert result["domain_category"] == "suspicious"
        assert len(result["flags"]) > 0
    
    def test_clickbait_title_chinese(self):
        """Test detection of Chinese clickbait titles."""
        result = evaluate_credibility.invoke({
            "url": "https://unknown-site.com/article",
            "title": "震惊！你绝对想不到的真相！",
        })
        
        assert result["score"] < 0.6
        assert "CLICKBAIT_TITLE" in result["flags"]
        assert any("诱导性" in reason for reason in result["reasons"])
    
    def test_clickbait_title_english(self):
        """Test detection of English clickbait titles."""
        result = evaluate_credibility.invoke({
            "url": "https://random-site.com/post",
            "title": "You won't believe what happened next!!!",
        })
        
        assert result["score"] < 0.6
        assert "CLICKBAIT_TITLE" in result["flags"]
    
    def test_excessive_punctuation(self):
        """Test detection of excessive punctuation."""
        result = evaluate_credibility.invoke({
            "url": "https://some-site.com/news",
            "title": "重大新闻！！！快看！！！",
        })
        
        assert "EXCESSIVE_PUNCTUATION" in result["flags"]
        assert result["score"] < 0.7
    
    def test_title_too_short(self):
        """Test flagging of very short titles."""
        result = evaluate_credibility.invoke({
            "url": "https://example.com/a",
            "title": "短标题",
        })
        
        assert "TITLE_TOO_SHORT" in result["flags"]
    
    def test_https_bonus(self):
        """Test that HTTPS gives a small bonus."""
        result_https = evaluate_credibility.invoke({
            "url": "https://neutral-site.com/article",
            "title": "Neutral article about something",
        })
        
        result_http = evaluate_credibility.invoke({
            "url": "http://neutral-site.com/article",
            "title": "Neutral article about something",
        })
        
        # HTTPS should score slightly higher
        assert result_https["score"] >= result_http["score"]
    
    def test_invalid_url(self):
        """Test handling of invalid URLs."""
        result = evaluate_credibility.invoke({
            "url": "not a url at all",
            "title": "Some title",
        })
        
        assert result["score"] == 0.0
        assert "URL_PARSE_ERROR" in result["flags"]
    
    def test_score_bounds(self):
        """Test that score is always between 0 and 1."""
        # Even with many negative factors
        result = evaluate_credibility.invoke({
            "url": "https://buzzfeed.com/clickbait",
            "title": "震惊！！！你绝对想不到！！！太牛了！！！",
        })
        
        assert 0.0 <= result["score"] <= 1.0


class TestEvaluateRelevance:
    """Tests for evaluate_relevance tool."""
    
    def test_ai_domain_high_relevance(self):
        """Test high relevance for AI content."""
        result = evaluate_relevance.invoke({
            "content": "GPT-4 和 Claude 是目前最先进的大模型，它们使用深度学习技术...",
            "domain": "AI",
        })
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "matched_keywords" in result
        
        assert result["score"] >= 0.5
        assert len(result["matched_keywords"]) > 0
    
    def test_tech_domain_relevance(self):
        """Test relevance for tech domain."""
        result = evaluate_relevance.invoke({
            "content": "新技术革新了整个行业，科技创新带来了数字化转型...",
            "domain": "科技",
        })
        
        assert result["score"] > 0.3
        assert any("科技" in kw or "技术" in kw or "创新" in kw 
                  for kw in result["matched_keywords"])
    
    def test_finance_domain_low_relevance(self):
        """Test low relevance when content doesn't match domain."""
        result = evaluate_relevance.invoke({
            "content": "今天天气很好，适合外出游玩，推荐大家去公园散步",
            "domain": "财经",
        })
        
        assert result["score"] < 0.5
        assert len(result["matched_keywords"]) == 0
    
    def test_query_matching(self):
        """Test that specific query improves relevance."""
        content = "特斯拉发布了新款电动汽车，续航里程达到500公里"
        
        result_with_query = evaluate_relevance.invoke({
            "content": content,
            "domain": "科技",
            "query": "特斯拉 电动汽车",
        })
        
        result_without_query = evaluate_relevance.invoke({
            "content": content,
            "domain": "科技",
        })
        
        # With matching query should score higher
        assert result_with_query["score"] >= result_without_query["score"]
    
    def test_content_length_penalty(self):
        """Test that very short content gets penalized."""
        result_short = evaluate_relevance.invoke({
            "content": "AI新闻",
            "domain": "AI",
        })
        
        result_long = evaluate_relevance.invoke({
            "content": "人工智能领域近期取得重大突破，新的大语言模型在多项任务上超越了人类表现，"
                      "展现出强大的推理和理解能力。研究团队表示这是机器学习技术的重要里程碑。",
            "domain": "AI",
        })
        
        # Longer content should score higher (all else equal)
        assert result_long["score"] > result_short["score"]
    
    def test_multiple_keyword_bonus(self):
        """Test bonus for multiple keyword matches."""
        result = evaluate_relevance.invoke({
            "content": "人工智能和机器学习技术在深度学习领域取得突破，"
                      "神经网络模型的性能大幅提升",
            "domain": "AI",
        })
        
        # Should match multiple AI keywords
        assert len(result["matched_keywords"]) >= 3
        assert result["score"] >= 0.6
    
    def test_unknown_domain(self):
        """Test handling of unknown domain."""
        result = evaluate_relevance.invoke({
            "content": "量子计算的最新进展",
            "domain": "量子计算",
        })
        
        # Should still work, using domain as keyword
        assert isinstance(result, dict)
        assert "score" in result
    
    def test_score_bounds(self):
        """Test that score is always between 0 and 1."""
        result = evaluate_relevance.invoke({
            "content": "完全无关的内容",
            "domain": "AI",
        })
        
        assert 0.0 <= result["score"] <= 1.0


def test_tools_have_descriptions():
    """Test that tools have proper descriptions for LLM."""
    assert evaluate_credibility.description
    assert evaluate_relevance.description
    assert "credibility" in evaluate_credibility.description.lower()
    assert "relevance" in evaluate_relevance.description.lower()

