# News Report Agent

<p align="center">
  <strong>AI-powered multi-agent news analysis and report generation system</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#web-ui">Web UI</a> •
  <a href="#cli">CLI</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/LangGraph-latest-green.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/React-19-61dafb.svg" alt="React 19">
  <img src="https://img.shields.io/badge/FastAPI-latest-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg" alt="MIT License">
</p>

---

## Overview

News Report Agent is a multi-agent AI system built on **LangGraph + DeepAgents** that automatically searches, filters, cross-reviews, and generates comprehensive news analysis reports. Given a query like "What's new in AI today?", it orchestrates multiple expert agents to deliver well-researched, fact-checked reports.

```
User Query → Query Planning → Multi-round Search → Credibility Filtering
          → Expert Analysis → Cross-review Council → Markdown Report
```

## Features

### Four Agentic Paradigms
- **Planning**: Task decomposition with `write_todos`
- **Reflection**: Three critical checkpoints for quality assurance
- **Tool Use**: Rich toolkit for search, scraping, and evaluation
- **Multi-Agent Collaboration**: 7 specialized expert agents + council

### Expert Agents
| Agent | Role |
|-------|------|
| `query_planner` | Generates 6-10 diverse search queries |
| `summarizer` | Extracts core points from articles |
| `fact_checker` | Verifies claims with sources |
| `researcher` | Provides background context |
| `impact_assessor` | Evaluates short/long-term impacts |
| `expert_supervisor` | Arbitrates between experts |
| `expert_council` | 4-phase cross-review process |

### Tools
- **Search**: Tavily, arXiv, GitHub, Hacker News, RSS feeds
- **Scraping**: httpx + BeautifulSoup content extraction
- **Evaluation**: Credibility & relevance grading (A/B/C/D)

### Interfaces
- **Web UI**: React frontend with real-time streaming progress
- **CLI**: Full-featured command line with checkpointing & tracing

---

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ (for Web UI)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/news-report-agent.git
cd news-report-agent

# Install Python dependencies
uv sync

# Configure environment
cp env.example .env
# Edit .env with your API keys (see Configuration section)

# Verify setup
uv run python check_env.py
```

### Configuration

Create a `.env` file with the following:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API Key | One of OpenAI/Azure |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI Key | One of OpenAI/Azure |
| `AZURE_OPENAI_ENDPOINT` | Azure endpoint URL | With Azure key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure deployment | With Azure key |
| `TAVILY_API_KEY` | Tavily search API | **Yes** |
| `GEMINI_KEY` | Google Gemini (for experts) | Optional |
| `NEWS_AGENT_FS_BASE` | Data directory | Optional (default: `./data`) |

---

## Web UI

The Web UI provides a modern, Apple-style interface with real-time streaming progress.

### Starting the Servers

**Option 1: Using start scripts**
```bash
# Terminal 1: Start backend (FastAPI on port 8000)
./start-backend.sh

# Terminal 2: Start frontend (React/Vite on port 5173)
./start-frontend.sh
```

**Option 2: Manual start**
```bash
# Backend
uv run uvicorn webui.backend.main:app --reload --port 8000

# Frontend
cd webui/frontend
npm install
npm run dev
```

### User Flow

The Web UI uses a **two-phase confirmation flow**:

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: Query Input                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  "What's new in AI today?"                    [Analyze]   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Phase 2: Review & Confirm Search Plan                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Intent Analysis:                                          │  │
│  │   • Understood query: Latest AI developments               │  │
│  │   • Time range: Past 7 days                                │  │
│  │   • Domain: Artificial Intelligence                        │  │
│  │   • Interests: [x] Tech breakthroughs  [x] Product launches│  │
│  │                                                            │  │
│  │  Search Plan:                                              │  │
│  │   • Tavily: "AI latest news December 2024"                 │  │
│  │   • arXiv: "artificial intelligence recent papers"         │  │
│  │   • GitHub: trending AI repositories                       │  │
│  │                                                            │  │
│  │  Exclude topics: [already known content]                   │  │
│  │  Additional context: [optional notes]                      │  │
│  │                                                            │  │
│  │                              [Cancel]  [Confirm & Execute] │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Phase 3: Real-time Streaming Progress                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🚀 Analysis started                           10:30:01   │  │
│  │  🔍 Web search: "AI latest news"               10:30:02   │  │
│  │  ✅ Search completed                           10:30:05   │  │
│  │  👤 summarizer: Extracting key points...       10:30:06   │  │
│  │  👤 fact_checker: Verifying claims...          10:30:08   │  │
│  │  👤 researcher: Gathering background...        10:30:10   │  │
│  │  ...                                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Phase 4: View Report                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📰 News Analysis Report                                   │  │
│  │  ─────────────────────────────────────────                 │  │
│  │  [Rendered HTML report with insights, facts, impacts]     │  │
│  │                                                            │  │
│  │                           [Download PDF]  [New Query]      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze/prepare` | POST | Phase 1: Analyze intent, return search plan |
| `/api/analyze/execute` | POST | Phase 2: Execute with user confirmation |
| `/api/stream/{task_id}` | GET | SSE stream for real-time progress |
| `/api/task/{task_id}` | GET | Get task status |
| `/api/report/{task_id}` | GET | Get HTML report |
| `/api/analyze` | POST | Quick mode (skip confirmation) |

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `QueryInput.jsx` | Query input form |
| `QueryConfirmation.jsx` | Search plan review & adjustment |
| `StreamingProgress.jsx` | Real-time progress display |
| `ReportViewer.jsx` | Report viewing & PDF export |

---

## CLI

The CLI provides full control with checkpointing and tracing capabilities.

### Basic Usage

```bash
# Simple query
uv run python -m cli.main "What's new in AI today?"

# With domain filter
uv run python -m cli.main --domain technology "Latest tech news"

# Save report to file
uv run python -m cli.main --output ./reports/today.md "AI developments"

# Verbose logging
uv run python -m cli.main --verbose "Tesla stock analysis"
```

### Advanced Features

```bash
# Enable checkpointing (resume sessions)
uv run python -m cli.main --checkpoint --thread-id daily-ai "AI news"

# Visual tracing (real-time + HTML export)
uv run python -m cli.main --trace --trace-output ./trace.html "Analysis"

# Full tracing with input/output details
uv run python -m cli.main --trace --trace-input --trace-output-detail "Query"
```

### CLI Options

| Option | Description |
|--------|-------------|
| `query` | The query to analyze (required) |
| `--domain` | Limit to domain: technology, finance, science, etc. |
| `--output, -o` | Save Markdown report to file |
| `--verbose, -v` | Show detailed logs |
| `--model` | Override default model |
| `--checkpoint` | Enable SQLite state persistence |
| `--checkpoint-dir` | Checkpoint storage directory |
| `--thread-id` | Session ID for resuming |
| `--trace, -t` | Enable visual tracing |
| `--trace-output` | Save trace to HTML/JSON |
| `--trace-input` | Show tool input details |
| `--trace-output-detail` | Show tool output details |

### Python API

```python
from src.agent import create_news_agent, create_news_agent_with_checkpointing

# Basic usage
agent = create_news_agent()
result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze today's AI news"}]
})
print(result["messages"][-1].content)

# With checkpointing
agent = create_news_agent_with_checkpointing(thread_id="daily-ai")
result = agent.invoke({
    "messages": [{"role": "user", "content": "Continue yesterday's analysis"}]
})
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            MasterAgent                                   │
│                     (LangGraph + DeepAgents)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Tools     │  │  Subagents  │  │   Council   │  │   Prompts   │    │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤    │
│  │ • search    │  │ • planner   │  │ • cross-    │  │ • master    │    │
│  │ • fetch     │  │ • summarize │  │   review    │  │ • experts   │    │
│  │ • evaluate  │  │ • fact_check│  │ • consensus │  │             │    │
│  │ • arxiv     │  │ • research  │  │ • synthesis │  │             │    │
│  │ • github    │  │ • impact    │  │             │  │             │    │
│  │ • hackernews│  │ • supervise │  │             │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
news-report-agent/
├── cli/                      # CLI entry point
│   └── main.py
├── webui/                    # Web UI
│   ├── backend/              # FastAPI server
│   │   ├── main.py           # API endpoints
│   │   └── sse_handler.py    # SSE callback handler
│   └── frontend/             # React app
│       └── src/
│           ├── App.jsx
│           └── components/
├── src/
│   ├── agent/                # Agent implementations
│   │   ├── master.py         # MasterAgent orchestration
│   │   ├── subagents/        # Expert agents
│   │   │   ├── query_planner.py
│   │   │   ├── summarizer.py
│   │   │   ├── fact_checker.py
│   │   │   ├── researcher.py
│   │   │   ├── impact_assessor.py
│   │   │   ├── expert_supervisor.py
│   │   │   ├── intent_analyzer.py      # WebUI Phase 1
│   │   │   └── search_plan_generator.py # WebUI Phase 1
│   │   └── council/          # Expert council
│   │       └── matrix.py     # Cross-review matrix
│   ├── prompts/              # System prompts
│   │   ├── master.py
│   │   └── experts.py
│   ├── tools/                # Tool implementations
│   │   ├── search.py         # Tavily search
│   │   ├── scraper.py        # Web scraping
│   │   ├── evaluator.py      # Credibility/relevance
│   │   └── sources/          # Multi-source tools
│   │       ├── arxiv.py
│   │       ├── github.py
│   │       ├── hackernews.py
│   │       └── rss.py
│   ├── schemas/              # Pydantic models
│   │   ├── base.py
│   │   └── outputs.py
│   ├── config.py             # Configuration loader
│   └── utils/                # Utilities
│       ├── tracer.py         # Execution tracing
│       ├── callbacks.py      # LangChain callbacks
│       └── templates.py      # Report formatting
├── tests/                    # Test suite
├── docs/                     # Documentation
├── data/                     # Default data directory
├── start-backend.sh          # Backend start script
├── start-frontend.sh         # Frontend start script
└── pyproject.toml
```

### Expert Council Process

The council implements a 4-phase cross-review process:

1. **Independent Analysis**: Experts complete their analyses
2. **Cross-Review**: Experts review each other based on the review matrix
3. **Consensus Discussion**: Address conflicts (C/D grades)
4. **Chairman Synthesis**: Final integrated verdict

Review dimensions: accuracy, completeness, consistency, evidence, logic

---

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Integration tests (requires API keys)
uv run pytest tests/ -v --run-integration

# Coverage report
uv run pytest tests/ --cov=src --cov-report=html
```

Tests use `skip_if_no_api_key` fixture to skip when API keys are unavailable.

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/PROJECT_GUIDE.md` | Project walkthrough |
| `docs/reference/AGENT_FLOW.md` | End-to-end execution flow |
| `docs/reference/DATETIME_CONTEXT.md` | Time context injection |
| `docs/EXPERT_COUNCIL_DESIGN.md` | Council mechanism design |
| `TESTING_GUIDE.md` | Testing strategy |
| `AGENTS.md` | Contributor guide |

---

## Contributing

Contributions are welcome! Please read `AGENTS.md` for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with LangGraph, DeepAgents, React, and FastAPI
</p>
