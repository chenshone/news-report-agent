"""MasterAgent creation and configuration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from ..config import AppConfig, create_chat_model, load_settings
from ..prompts import MASTER_AGENT_SYSTEM_PROMPT
from ..tools import (
    evaluate_credibility,
    evaluate_relevance,
    fetch_page,
    fetch_rss_feeds,
    get_hackernews_top,
    internet_search,
    search_arxiv,
    search_github_repos,
    search_github_trending,
    search_hackernews,
)
from .subagents import get_subagent_configs


def create_news_agent(
    config: AppConfig | None = None,
    additional_tools: list[BaseTool] | None = None,
    model_override: BaseChatModel | None = None,
    current_datetime: datetime | None = None,
    use_structured_output: bool = True,
    include_direct_experts: bool = True,
    **kwargs: Any,
) -> Any:
    """
    Create a news report MasterAgent with full Agentic AI capabilities.

    The agent embodies four paradigms:
    - Planning: Uses write_todos to create and manage task lists
    - Reflection: Evaluates progress at checkpoints and adjusts strategy
    - Tool Use: Leverages search, scraping, and evaluation tools
    - Multi-Agent Collaboration: Dispatches expert subagents via task()

    Args:
        config: Application configuration. If None, loads from environment.
        additional_tools: Extra tools to register beyond the default set.
        model_override: Override the model with a BaseChatModel instance.
        current_datetime: Current date and time. If None, uses datetime.now().
        use_structured_output: Whether to use Pydantic-based structured output.
        include_direct_experts: Whether to mount single expert subagents.
        **kwargs: Additional arguments passed to create_deep_agent.

    Returns:
        A configured DeepAgents agent instance.
    """
    if config is None:
        config = load_settings()

    if current_datetime is None:
        current_datetime = datetime.now()

    if model_override:
        model = model_override
    else:
        master_model_config = config.model_for_role("master")
        model = create_chat_model(master_model_config, config)

    # Core tools
    tools: list[BaseTool] = [
        internet_search,
        fetch_page,
        evaluate_credibility,
        evaluate_relevance,
        # Multi-source intelligence tools
        search_arxiv,
        search_github_repos,
        search_github_trending,
        search_hackernews,
        get_hackernews_top,
        fetch_rss_feeds,
    ]

    if additional_tools:
        tools.extend(additional_tools)

    subagent_configs = get_subagent_configs(
        config,
        use_structured_output=use_structured_output,
        include_direct_experts=include_direct_experts,
    )

    datetime_info = format_datetime_context(current_datetime)

    enhanced_system_prompt = f"""{MASTER_AGENT_SYSTEM_PROMPT}

## 当前日期时间信息

{datetime_info}

**重要提示**：
- 当用户提到"今天"、"近期"、"最新"等时间词时，参考上述日期时间
- 将这个信息传递给 query_planner，让它生成带时间限定的查询
- 例如：用户说"今天AI进展" → query_planner 应生成 "AI 2024年12月15日 最新进展"
"""

    return create_deep_agent(
        model=model,
        system_prompt=enhanced_system_prompt,
        tools=tools,
        subagents=subagent_configs,
        **kwargs,
    )


def format_datetime_context(dt: datetime) -> str:
    """Format datetime information for agent context in Chinese."""
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[dt.weekday()]

    date_str = dt.strftime("%Y年%m月%d日")
    time_str = dt.strftime("%H:%M:%S")
    yesterday_str = (dt - timedelta(days=1)).strftime("%Y年%m月%d日")

    return f"""当前日期：{date_str} ({weekday})
当前时间：{time_str}

时间参考：
- "今天" 指的是 {date_str}
- "昨天" 指的是 {yesterday_str}
- "近期" 通常指最近 7 天左右
- "最新" 通常指最近 24-48 小时"""


def create_news_agent_with_checkpointing(
    checkpoint_dir: str | None = None,
    thread_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Create a news agent with persistent checkpointing for long-running tasks.

    Uses LangGraph's checkpointing to save state between invocations,
    allowing the agent to resume work after interruptions.

    Args:
        checkpoint_dir: Directory for saving checkpoints. Defaults to ./data/checkpoints.
        thread_id: Unique identifier for the conversation thread.
        **kwargs: Additional arguments passed to create_news_agent.

    Returns:
        A configured agent with checkpointing enabled.
    """
    import sqlite3
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver

    if checkpoint_dir is None:
        checkpoint_dir = "./data/checkpoints"

    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

    checkpoint_path = f"{checkpoint_dir}/agent_state.db"
    conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return create_news_agent(checkpointer=checkpointer, **kwargs)


__all__ = [
    "create_news_agent",
    "create_news_agent_with_checkpointing",
]
