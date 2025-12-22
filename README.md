# 热点资讯聚合 Agentic AI

基于 LangGraph + DeepAgents 的多智能体新闻分析系统，自动搜索、筛选、交叉评审并生成 Markdown 格式的热点资讯报告。

## 功能亮点
- **四大 Agentic 范式**：规划（write_todos）、反思检查点、工具调用、专家协作。
- **多专家协作**：查询规划、摘要、事实核查、背景研究、影响评估、专家主管，另有一键触发的 `expert_council` 四阶段流程（独立分析→交叉评审→共识讨论→主管裁决）。
- **结构化输出**：关键子 Agent 使用 Pydantic schema（`src/schemas/outputs.py`）确保结果可解析，可选纯文本模式。
- **工具链**：Tavily 搜索、网页抓取（httpx+bs4）、可信度/相关性评估（A/B/C/D 等级制）。
- **运行体验**：CLI 支持持久化 checkpoint、实时可视化追踪（HTML/JSON 导出）、自定义输出路径。

## 快速开始
### 环境要求
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 安装与配置
```bash
# 获取代码
git clone https://github.com/yourusername/news-report-agent.git
cd news-report-agent

# 安装依赖（推荐）
uv sync

# 准备配置
cp env.example .env
# 至少设置：OPENAI_API_KEY 或 Azure 组合，TAVILY_API_KEY
# 可选：GEMINI_KEY + MODEL_GEMINI_3_FLASH（专家用 Gemini），NEWS_AGENT_FS_BASE=./data
```

### 验证环境
```bash
uv run python check_env.py
# 可选：快速跑一次测试（无真实 key 会跳过部分用例）
uv run pytest tests/ -v
```

## 使用说明
### 命令行（推荐）
```bash
# 基础查询
uv run python -m cli.main "今天AI领域有什么进展"

# 指定领域 / 输出文件 / 详细日志
uv run python -m cli.main --domain technology --output ./reports/today.md "最新科技新闻"
uv run python -m cli.main --verbose "分析特斯拉股价"

# 持久化 checkpoint（SQLite，默认 ${NEWS_AGENT_FS_BASE:-./data}/checkpoints/agent_state.db）
uv run python -m cli.main --checkpoint --thread-id daily-ai "今天AI领域有什么进展"
# 未提供 --thread-id 时会基于查询自动生成哈希，便于同主题续跑

# 可视化追踪（终端实时 + 导出 HTML/JSON）
uv run python -m cli.main --trace --trace-output ./reports/trace.html "分析 Sora 最新更新"
uv run python -m cli.main --trace --trace-input --trace-output-detail "今天科技圈有什么重要进展"

# 安装的可执行脚本
uv run news-agent "今天有什么AI新闻"
```
> 注意：`--model` 参数当前预留，实际模型切换请通过环境变量/配置完成。

### Python API
```python
from src.agent import create_news_agent, create_news_agent_with_checkpointing

agent = create_news_agent()
result = agent.invoke({"messages": [{"role": "user", "content": "分析今天AI热点"}]})
print(result["messages"][-1].content)

# 启用 checkpoint（可跨多次运行复用状态）
agent_ckpt = create_news_agent_with_checkpointing(thread_id="daily-ai")
ag_result = agent_ckpt.invoke({"messages": [{"role": "user", "content": "复盘昨日科技要闻"}]})
```

## 架构与组件
- **MasterAgent**（`src/agent/master.py`）：基于 `create_deep_agent`，加载 `src/prompts/master.py`，执行规划/反思/工具调用，注入当前日期时间。
- **子 Agent（`src/agent/subagents/`）**：
  - `query_planner`（`QueryPlannerOutput`）
  - `summarizer`（`SummaryOutput`）
  - `fact_checker`（使用 `internet_search`）
  - `researcher`（使用 `internet_search`）
  - `impact_assessor`（`ImpactAssessorOutput`）
  - `expert_supervisor`（`SupervisorOutput`）
  - `expert_council`（封装四阶段协作，全流程自动输出报告）
- **交叉评审矩阵**：`src/agent/council/matrix.py` 定义 reviewer/被评审者关系与维度。
- **工具**（`src/tools/`）：`internet_search`(Tavily)、`fetch_page`/`fetch_page_async`、`evaluate_credibility`、`evaluate_relevance`（A/B/C/D）。
- **提示词与模板**：`src/prompts/` 存放系统/专家 prompt；`src/utils/templates.py` 生成 Markdown 报告与终端输出。
- **追踪与回调**：`src/utils/tracer.py` 提供事件追踪、Rich 终端可视化、HTML/JSON 导出；`src/utils/callbacks.py` 提供默认日志回调。

### 目录结构
```
news-report-agent/
├── cli/main.py                # CLI 入口（trace / checkpoint / 输出路径）
├── src/
│   ├── agent/                 # Master + SubAgents + Council
│   │   ├── master.py
│   │   ├── subagents/         # 各专家 & expert_council
│   │   └── council/           # 交叉评审矩阵等
│   ├── prompts/               # master/experts 提示词
│   ├── tools/                 # 搜索、抓取、评估工具
│   ├── schemas/               # 基础与结构化输出模型
│   └── utils/                 # 日志、回调、追踪、报告模板
├── tests/                     # 单元/集成测试（见 TESTING_GUIDE.md）
├── docs/                      # 设计文档（如 EXPERT_COUNCIL_DESIGN）
├── reports/                   # 示例/输出目录
├── data/                      # 默认持久化目录（NEWS_AGENT_FS_BASE）
├── AGENTS.md                  # 贡献者指南
└── TESTING_GUIDE.md           # 测试策略与命令
```

## 配置说明
| 变量名 | 说明 | 必需 |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI API Key | 二选一（与 Azure） |
| `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI 配置 | 二选一（与 OpenAI） |
| `GEMINI_KEY` / `MODEL_GEMINI_3_FLASH` | 使用 Google Gemini 作为专家模型（Master 仍用 OpenAI/Azure） | 可选 |
| `TAVILY_API_KEY` | Tavily 搜索 | ✅ |
| `BRAVE_API_KEY`, `FIRECRAWL_API_KEY` | 预留的搜索/抓取备用 Key | 可选 |
| `NEWS_AGENT_FS_BASE` | 文件系统根目录，包含 checkpoints/reports 等 | 可选（默认 `./data`） |

配置规则：若提供 Azure 配置，则 Master/专家默认使用 Azure；若额外提供 Gemini 配置，专家角色切换到 Gemini，Master 仍使用 OpenAI/Azure。

## 追踪与持久化
- `--checkpoint`：启用 SQLite checkpointer（`<NEWS_AGENT_FS_BASE>/checkpoints/agent_state.db`），可通过 `--thread-id` 控制会话隔离。
- `--trace`：终端实时树状可视化；`--trace-output` 支持 `.html` 或 `.json`，若目录不存在会自动创建；`--trace-input/--trace-output-detail` 控制输入输出详情。

## 测试
- 快速运行：`uv run pytest tests/ -v`
- 集成测试（需要真实 API keys）：`uv run pytest tests/ -v --run-integration`
- 覆盖率：`uv run pytest tests/ --cov=src --cov-report=html`，查看 `htmlcov/index.html`
- `skip_if_no_api_key` 会在缺少 `OPENAI_API_KEY`/Azure 与 `TAVILY_API_KEY` 时跳过相关用例；尽量使用轻量模型与短提示降低成本。

## 进一步阅读
- `docs/PROJECT_GUIDE.md`：当前项目解读（建议从这里开始）
- `docs/reference/AGENT_FLOW.md`：端到端运行流程
- `docs/reference/DATETIME_CONTEXT.md`：时间上下文注入规则
- `docs/EXPERT_COUNCIL_DESIGN.md`：四阶段专家协作机制
- `docs/archive/`：历史阶段/旧设计文档（可能过时）
- `AGENTS.md`：贡献者指南与提交规范
- `TESTING_GUIDE.md`：测试策略与示例

## 贡献与许可证
欢迎提交 Issue/PR，提交前请阅读 `AGENTS.md` 并附上关键测试命令。项目使用 MIT License。
