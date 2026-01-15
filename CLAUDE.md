# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Multi-agent AI system for automated news analysis and report generation. Given a query (e.g., "今天AI领域有什么进展"), executes: **query planning -> multi-round search -> credibility/relevance filtering -> multi-expert analysis -> (optional) expert council cross-review -> Markdown report**.

Built on LangGraph + DeepAgents with four agentic paradigms: planning (write_todos), reflection checkpoints, tool use, and multi-agent collaboration.

## Commands

```bash
# Setup
uv sync                                    # Install dependencies
uv run python check_env.py                 # Verify environment

# Tests
uv run pytest tests/ -v                    # All tests (skips if no API keys)
uv run pytest tests/ -v --run-integration  # Integration tests (requires API keys)
uv run pytest tests/ --cov=src --cov-report=html  # Coverage report

# CLI
uv run python -m cli.main "今天AI领域有什么进展"
uv run python -m cli.main --domain technology --output ./reports/today.md "最新科技新闻"
uv run python -m cli.main --trace --trace-output ./reports/trace.html "分析热点"
uv run python -m cli.main --checkpoint --thread-id daily-ai "今天AI领域有什么进展"
```

## Architecture

### Core Components

| Component | Location | Description |
|-----------|----------|-------------|
| **MasterAgent** | `src/agent/master.py` | Orchestrates workflow via `create_deep_agent`, injects datetime context |
| **Subagents** | `src/agent/subagents/` | See below |
| **Tools** | `src/tools/` | `internet_search`, `fetch_page`, `evaluate_credibility/relevance` |
| **Prompts** | `src/prompts/` | System prompts for master and experts |
| **Schemas** | `src/schemas/` | Pydantic output models, base types (GradeType: A/B/C/D) |

### Subagents

- `query_planner`: Generates 6-10 diverse search queries
- `summarizer`: Extracts core points from articles
- `fact_checker`: Verifies claims (has `internet_search` tool)
- `researcher`: Provides background context (has `internet_search` tool)
- `impact_assessor`: Evaluates short/long-term impacts
- `expert_supervisor`: Final integration and arbitration
- `expert_council`: 4-phase process (independent analysis -> cross-review -> consensus -> chairman synthesis)

### Cross-Review Matrix

`src/agent/council/matrix.py` defines expert peer review dimensions (accuracy, completeness, consistency, evidence, logic).

## Configuration

Loads from environment via `src/config.py:load_settings()`.

**Required:**
- `TAVILY_API_KEY`
- One of: `OPENAI_API_KEY` OR Azure trio (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`)

**Optional:**
- `GEMINI_KEY` + `MODEL_GEMINI_3_FLASH`: Expert agents use Gemini while Master stays on OpenAI/Azure
- `NEWS_AGENT_FS_BASE`: Filesystem root for checkpoints (default: `./data`)

## Key Patterns

- **Model Routing**: Master uses OpenAI/Azure; experts can use Gemini if configured. Use `create_chat_model(model_config, app_config)` for provider dispatch.
- **Datetime Injection**: `format_datetime_context()` enables time-aware queries ("今天", "近期", "最新").
- **Structured Output**: Subagents use `model.with_structured_output()` with Pydantic schemas.
- **Test Strategy**: Real integration tests (not mocks); `skip_if_no_api_key` fixture; cost-controlled via `gpt-4o-mini`.

## Extension Points

**Add a new tool:**
1. Create function with `@tool` decorator in `src/tools/`
2. Export in `src/tools/__init__.py`
3. Register in `create_news_agent()` tools list

**Add a new expert:**
1. Add prompt in `src/prompts/experts.py`
2. Add Pydantic output model in `src/schemas/outputs.py`
3. Create subagent in `src/agent/subagents/` and register in `get_subagent_configs()`
4. Update `src/prompts/master.py` workflow description

## Code Style

- Python 3.11+, PEP8, 4-space indent
- Type hints and concise docstrings
- `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Favor pure functions and explicit config
- Never log secrets
