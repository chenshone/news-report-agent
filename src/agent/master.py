"""MasterAgent creation and configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from ..config import AppConfig, create_chat_model, load_settings
from ..tools import (
    evaluate_credibility,
    evaluate_relevance,
    fetch_page,
    internet_search,
)
from ..prompts import MASTER_AGENT_SYSTEM_PROMPT
from .subagents import get_subagent_configs


def create_news_agent(
    config: Optional[AppConfig] = None,
    additional_tools: Optional[List[BaseTool]] = None,
    model_override: Optional[BaseChatModel] = None,
    current_datetime: Optional[datetime] = None,
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
        use_structured_output: Whether to use Pydantic-based structured output
            for expert subagents. Defaults to True (recommended).
        include_direct_experts: Whether to mount single expert subagents
            (summarizer/fact_checker/researcher/impact_assessor/supervisor).
            Defaults to True to allow pre-analysis before expert_council.
        **kwargs: Additional arguments passed to create_deep_agent.
        
    Returns:
        A configured DeepAgents agent instance.
        
    Example:
        >>> agent = create_news_agent()
        >>> result = agent.invoke({
        ...     "messages": [{"role": "user", "content": "分析今天AI领域热点"}]
        ... })
        >>> print(result["messages"][-1].content)
    """
    # Load configuration
    if config is None:
        config = load_settings()
    
    # Get current datetime
    if current_datetime is None:
        current_datetime = datetime.now()
    
    # Determine the model to use
    if model_override:
        # Use the provided BaseChatModel instance
        model = model_override
    else:
        # Use config to create a properly configured ChatModel instance
        master_model_config = config.model_for_role("master")
        model = create_chat_model(master_model_config, config)
    
    # Collect custom tools
    tools: List[BaseTool] = [
        # 搜索与获取
        internet_search,
        fetch_page,
        # 评估
        evaluate_credibility,
        evaluate_relevance,
        # 注：expert_council 仅负责互评/共识/裁决，需先产出专家独立分析
        # 使用 task("summarizer"/"fact_checker"/"researcher"/"impact_assessor") 后再 task("expert_council", ...)
    ]
    
    if additional_tools:
        tools.extend(additional_tools)
    
    # Get expert subagent configurations
    subagent_configs = get_subagent_configs(
        config,
        use_structured_output=use_structured_output,
        include_direct_experts=include_direct_experts,
    )
    
    # Format datetime information for the system prompt
    datetime_info = format_datetime_context(current_datetime)
    
    # Inject datetime into system prompt
    enhanced_system_prompt = f"""{MASTER_AGENT_SYSTEM_PROMPT}

## 当前日期时间信息

{datetime_info}

**重要提示**：
- 当用户提到"今天"、"近期"、"最新"等时间词时，参考上述日期时间
- 将这个信息传递给 query_planner，让它生成带时间限定的查询
- 例如：用户说"今天AI进展" → query_planner 应生成 "AI 2024年12月15日 最新进展"
"""
    
    # Create agent with DeepAgents
    # model can be either a string or BaseChatModel instance
    agent = create_deep_agent(
        model=model,
        system_prompt=enhanced_system_prompt,
        tools=tools,
        subagents=subagent_configs,
        **kwargs,
    )
    
    return agent


def format_datetime_context(dt: datetime) -> str:
    """
    Format datetime information for agent context.
    
    Args:
        dt: Datetime object
        
    Returns:
        Formatted string with date, time, and day of week in Chinese
    """
    # Day of week in Chinese
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[dt.weekday()]
    
    # Format datetime
    date_str = dt.strftime("%Y年%m月%d日")
    time_str = dt.strftime("%H:%M:%S")
    
    return f"""当前日期：{date_str} ({weekday})
当前时间：{time_str}

时间参考：
- "今天" 指的是 {date_str}
- "昨天" 指的是 {(dt - __import__('datetime').timedelta(days=1)).strftime("%Y年%m月%d日")}
- "近期" 通常指最近 7 天左右
- "最新" 通常指最近 24-48 小时"""


def create_news_agent_with_checkpointing(
    checkpoint_dir: Optional[str] = None,
    thread_id: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Create a news agent with persistent checkpointing for long-running tasks.
    
    This variant uses LangGraph's checkpointing to save state between invocations,
    allowing the agent to resume work after interruptions.
    
    Args:
        checkpoint_dir: Directory for saving checkpoints. Defaults to ./data/checkpoints
        thread_id: Unique identifier for the conversation thread.
        **kwargs: Additional arguments passed to create_news_agent.
        
    Returns:
        A configured agent with checkpointing enabled.
        
    Example:
        >>> agent = create_news_agent_with_checkpointing(thread_id="daily-report-001")
        >>> # Agent state is persisted across runs
    """
    import sqlite3
    from langgraph.checkpoint.sqlite import SqliteSaver
    from pathlib import Path
    
    # Set up checkpoint directory
    if checkpoint_dir is None:
        checkpoint_dir = "./data/checkpoints"

    # Ensure directory exists (SqliteSaver won't create parent dirs)
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    # Create checkpointer with direct sqlite3 connection
    # Note: from_conn_string() returns a context manager; use direct connection instead
    checkpoint_path = f"{checkpoint_dir}/agent_state.db"
    conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    
    # Create agent with checkpointing
    agent = create_news_agent(
        checkpointer=checkpointer,
        **kwargs,
    )
    
    return agent


__all__ = [
    "create_news_agent",
    "create_news_agent_with_checkpointing",
]
