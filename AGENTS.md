# Repository Guidelines

## Project Structure & Module Organization
- `src/agent/` hosts master agent factory, expert subagents, and orchestration prompts; `src/tools/` covers search, scraping, and evaluators; `src/utils/` keeps logging/templates; `src/schemas/` defines typed payloads; `src/prompts/` stores system prompt text.
- `cli/main.py` is the CLI entry; `tests/` mirrors code areas (`agent/`, `tools/`, `integration/`, `cli/`); `docs/` and root `*.md` capture design phases; `data/` is the default workspace for checkpoints; generated reports live under `reports/`.

## Build, Test, and Development Commands
- Install: `uv sync`; sanity-check env: `uv run python check_env.py`.
- Run locally: `uv run python -m cli.main "今天AI领域有什么进展"` or `uv run news-agent "..."` via console script.
- Tests: `uv run pytest tests/ -v`; run full/integration suite with real API keys: `uv run pytest tests/ -v --run-integration`.
- Coverage: `uv run pytest tests/ --cov=src --cov-report=html` then open `htmlcov/index.html`; for focused debug use `uv run pytest tests/<area>/ -v -s`.

## Coding Style & Naming Conventions
- Python 3.11+, PEP8 with 4-space indent; keep type hints and concise docstrings consistent with `src/agent/master.py`.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes/Pydantic models, constants `UPPER_SNAKE_CASE`.
- Place new prompts in `src/prompts`, schemas in `src/schemas`; add tools under `src/tools/`, export in `__init__.py`, and register through `create_news_agent`.
- Favor pure functions and explicit config; avoid logging secrets (loguru setup in `src/utils/logger.py`).

## Testing Guidelines
- Use pytest; store new tests beside related code with `test_*.py` files and descriptive test names.
- For API-dependent paths, apply `skip_if_no_api_key` and keep prompts short/`temperature=0` to control cost.
- Add unit coverage for pure logic before integration cases; integration tests should assert end-to-end agent behavior and may be gated by `--run-integration`.

## Commit & Pull Request Guidelines
- Commits: short, imperative, scoped (e.g., `Add search retry`, `Refine expert prompts`); avoid bundling unrelated changes.
- PRs: summarize change/impact, link an issue when available, list commands/tests run (`uv run pytest ...`), and call out any env/config or documentation updates.
- If prompts/tools/checkpoint paths change, attach a sample CLI run or generated report path so reviewers can verify output.

## Security & Configuration Tips
- Copy `env.example` to `.env`; never commit secrets. Required keys: OpenAI/Azure plus `TAVILY_API_KEY`; optional Gemini keys if using mixed providers.
- Override `NEWS_AGENT_FS_BASE` to control checkpoint location; keep API responses and keys out of tracked files.
- Re-run `uv run python check_env.py` after env changes before executing agents or tests.
