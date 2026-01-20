# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Multi-agent AI system for automated news analysis and report generation. Given a query (e.g., "今天AI领域有什么进展"), executes: **query planning -> multi-round search -> credibility/relevance filtering -> multi-expert analysis -> (optional) expert council cross-review -> Markdown report**.

Built on LangGraph + DeepAgents with four agentic paradigms: planning (write_todos), reflection checkpoints, tool use, and multi-agent collaboration.

**Two interfaces available:**
- **Web UI** (primary): React frontend + FastAPI backend with SSE streaming
- **CLI**: Command line with checkpointing & tracing

## Commands

```bash
# Setup
uv sync                                    # Install dependencies
uv run python check_env.py                 # Verify environment

# Tests
uv run pytest tests/ -v                    # All tests (skips if no API keys)
uv run pytest tests/ -v --run-integration  # Integration tests (requires API keys)
uv run pytest tests/ --cov=src --cov-report=html  # Coverage report

# Web UI (primary interface)
./start-backend.sh                         # Backend: FastAPI on port 8000
./start-frontend.sh                        # Frontend: React/Vite on port 5173
# Or manually:
uv run uvicorn webui.backend.main:app --reload --port 8000
cd webui/frontend && npm install && npm run dev

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
| **Tools** | `src/tools/` | `internet_search`, `fetch_page`, `evaluate_credibility/relevance`, multi-source tools |
| **Prompts** | `src/prompts/` | System prompts for master and experts |
| **Schemas** | `src/schemas/` | Pydantic output models, base types (GradeType: A/B/C/D) |

### Web UI Components

| Component | Location | Description |
|-----------|----------|-------------|
| **Backend API** | `webui/backend/main.py` | FastAPI endpoints for analyze/stream/report |
| **SSE Handler** | `webui/backend/sse_handler.py` | LangChain callback -> SSE events |
| **Frontend App** | `webui/frontend/src/App.jsx` | Main React app with 4-phase flow |
| **QueryInput** | `webui/frontend/src/components/QueryInput.jsx` | Query input form |
| **QueryConfirmation** | `webui/frontend/src/components/QueryConfirmation.jsx` | Search plan review UI |
| **StreamingProgress** | `webui/frontend/src/components/StreamingProgress.jsx` | Real-time progress display |
| **ReportViewer** | `webui/frontend/src/components/ReportViewer.jsx` | Report view + PDF export |

### Web UI Flow (Two-Phase Confirmation)

```
Phase 1: /api/analyze/prepare (POST)
  - User submits query
  - Backend analyzes intent, generates search plan
  - Returns: task_id, intent_analysis, search_plan

Phase 2: /api/analyze/execute (POST)
  - User confirms/adjusts plan
  - Backend executes full agent workflow
  - Returns: task_id for SSE streaming

SSE Stream: /api/stream/{task_id} (GET)
  - Real-time events: agent_start, tool_start/end, subagent_start/end, report
  - Frontend displays progress and final report
```

### Subagents

**Core experts:**
- `query_planner`: Generates 6-10 diverse search queries
- `summarizer`: Extracts core points from articles
- `fact_checker`: Verifies claims (has `internet_search` tool)
- `researcher`: Provides background context (has `internet_search`, `search_arxiv`, `search_github_repos` tools)
- `impact_assessor`: Evaluates short/long-term impacts
- `expert_supervisor`: Final integration and arbitration
- `expert_council`: 4-phase process (independent analysis -> cross-review -> consensus -> chairman synthesis)
- `report_synthesizer`: Integrates expert outputs into insight-driven reports

**WebUI-specific (Phase 1):**
- `intent_analyzer`: Analyzes user intent (time range, domain, interests)
- `search_plan_generator`: Generates search plan (sources, queries, priorities)

### Multi-Source Tools

| Tool | Location | Description |
|------|----------|-------------|
| `internet_search` | `src/tools/search.py` | Tavily web search |
| `fetch_page` | `src/tools/scraper.py` | Web content extraction |
| `evaluate_credibility` | `src/tools/evaluator.py` | Source credibility grading |
| `evaluate_relevance` | `src/tools/evaluator.py` | Content relevance grading |
| `search_arxiv` | `src/tools/sources/arxiv.py` | Academic paper search |
| `search_github_repos` | `src/tools/sources/github.py` | GitHub repository search |
| `search_github_trending` | `src/tools/sources/github.py` | Trending repos |
| `search_hackernews` | `src/tools/sources/hackernews.py` | HN story search |
| `get_hackernews_top` | `src/tools/sources/hackernews.py` | Top HN stories |
| `fetch_rss_feeds` | `src/tools/sources/rss.py` | RSS feed aggregation |

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
- **SSE Streaming**: `SSECallbackHandler` converts LangChain callbacks to SSE events for real-time frontend updates.
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

**Add a new API endpoint:**
1. Add route in `webui/backend/main.py`
2. Update frontend components if UI changes needed

**Add SSE event type:**
1. Add to `SSEEventType` enum in `webui/backend/sse_handler.py`
2. Handle in `SSECallbackHandler` methods
3. Update `StreamingProgress.jsx` to display new event type

## Directory Structure

```
news-report-agent/
├── cli/main.py                    # CLI entry point
├── webui/
│   ├── backend/
│   │   ├── main.py                # FastAPI app & endpoints
│   │   └── sse_handler.py         # SSE callback handler
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx            # Main app component
│       │   ├── components/        # React components
│       │   └── styles/            # CSS styles
│       └── package.json
├── src/
│   ├── agent/
│   │   ├── master.py              # MasterAgent
│   │   ├── subagents/             # Expert subagents
│   │   └── council/               # Cross-review matrix
│   ├── prompts/                   # System prompts
│   ├── tools/                     # Tool implementations
│   │   └── sources/               # Multi-source tools
│   ├── schemas/                   # Pydantic models
│   ├── config.py                  # Configuration
│   └── utils/                     # Utilities
├── tests/                         # Test suite
├── docs/                          # Documentation
├── start-backend.sh               # Backend start script
├── start-frontend.sh              # Frontend start script
└── pyproject.toml
```

## Code Style

- Python 3.11+, PEP8, 4-space indent
- Type hints and concise docstrings
- `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Favor pure functions and explicit config
- Never log secrets
- Frontend: React functional components with hooks, JSX
