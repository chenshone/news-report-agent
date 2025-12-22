# 📚 项目解读（最新版）

> 本文以“当前代码即真相”为准，按 `src/` 与 `cli/` 的实际实现梳理项目结构、执行链路、配置方式与扩展点。  
> 历史阶段文档已迁移至 `docs/archive/`（可能过时）。

## 1. 这个项目解决什么问题？

`news-report-agent` 是一个面向“热点资讯/专题追踪”的 Agentic AI 系统：输入一句查询（如“今天 AI 领域有什么进展”），它会自动完成 **规划 → 多轮检索 → 可信度/相关性筛选 → 多专家分析 →（可选）专家委员会互评与共识 → Markdown 报告输出**。

核心目标不是“回答一个问题”，而是 **用可追踪、可复盘的工作流产出有证据链的新闻解读报告**。

## 2. 代码结构一眼看懂

```
cli/
  main.py                    # CLI 入口：trace / checkpoint / 输出文件
src/
  agent/
    master.py                # create_news_agent：装配 MasterAgent + 工具 + 子Agent
    subagents/               # query_planner / summarizer / fact_checker / researcher / impact_assessor / supervisor / council
    council/                 # 交叉评审矩阵与 Prompt 模板（给 expert_council 使用）
  prompts/
    master.py                # MASTER_AGENT_SYSTEM_PROMPT（工作流与报告规范的“总指挥”）
    experts.py               # 各专家提示词（含 structured/非 structured 版本）
  tools/
    search.py                # internet_search（Tavily）
    scraper.py               # fetch_page（网页正文抽取）
    evaluator.py             # evaluate_credibility / evaluate_relevance（A/B/C/D）
  schemas/
    outputs.py               # Pydantic 结构化输出（QueryPlannerOutput 等）
  utils/
    templates.py             # CLI 写文件时的 Markdown 包装
    tracer.py                # trace：终端实时可视化 + HTML/JSON 导出
    logger.py                # loguru 日志
```

你只要抓住两条主线：
- **系统行为的上限**：由 `src/prompts/master.py`（总提示词）定义
- **系统能力的边界**：由 `src/agent/master.py` 注册的 tools + subagents 决定

## 3. 端到端执行链路（从 CLI 到报告）

以 `uv run python -m cli.main "今天AI领域有什么进展"` 为例：

1. `cli/main.py` 解析参数（`--domain/--output/--trace/--checkpoint/...`）
2. `src/config.py:load_settings()` 从 `.env` / 环境变量加载：
   - OpenAI / Azure OpenAI（master 默认）
   - 可选 Gemini（作为专家模型）
   - `NEWS_AGENT_FS_BASE`（默认 `./data`，用于 checkpoint 等）
3. `src/agent/master.py:create_news_agent()` 装配：
   - system prompt：`src/prompts/master.py:MASTER_AGENT_SYSTEM_PROMPT` + “当前日期时间注入”
   - tools：`internet_search` / `fetch_page` / `evaluate_credibility` / `evaluate_relevance`
   - subagents：`src/agent/subagents/*`（含 `expert_council`）
4. MasterAgent 开始执行（由 system prompt 约束行为）：
   - `query_planner` 先生成 6–10 个多角度 query
   - 多轮搜索与抓取：`internet_search` →（必要时）`fetch_page`
   - 筛选：`evaluate_credibility` + `evaluate_relevance`（A/B/C/D）
   - 深度分析：对重点新闻调用 `expert_council`（推荐默认），或按需调用单专家
   - 整合：输出一次性完整 Markdown 报告
5. CLI 输出：
   - 终端：直接打印最后一条 AI 消息（`src/utils/templates.py:format_simple_output`）
   - 文件：在 AI 报告外再包一层头尾（`format_markdown_report`）

## 4. 关键机制：为什么它“更像做事的团队”

### 4.1 规划与反思（Planning / Reflection）

MasterAgent 被强制要求：
- **先规划**：用 `write_todos` 写清任务清单（搜索/筛选/分析/整合）
- **后执行**：并在搜索后、筛选后、分析后做反思检查点
- **不够就补**：例如原始搜索结果不足时，必须回到搜索补齐

这些行为都在 `src/prompts/master.py` 明确写死：模型不遵守就更容易被 prompt “拉回正轨”。

### 4.2 工具链（Tool Use）

项目有两类工具：
- DeepAgents 内置：`write_todos/read_todos`、文件系统（`write_file/read_file/grep/ls/...`）、`task()` 派生子Agent
- 项目自定义：
  - `src/tools/search.py:internet_search`：Tavily 搜索（建议 `max_results=8~10`）
  - `src/tools/scraper.py:fetch_page`：网页正文抽取（适合补全摘要）
  - `src/tools/evaluator.py:evaluate_credibility/evaluate_relevance`：启发式 A/B/C/D 评分

> 设计取舍：评估工具是“轻量启发式”，用于快速过滤与排序，不是最终事实裁判。

### 4.3 多专家协作（Multi-Agent Collaboration）

子 Agent 在 `src/agent/subagents/`：

- `query_planner`：生成多角度查询（结构化输出：`QueryPlannerOutput`）
- `summarizer`：摘要（结构化输出：`SummaryOutput`）
- `fact_checker`：事实核查（带 `internet_search` 工具）
- `researcher`：背景研究（带 `internet_search` 工具）
- `impact_assessor`：影响评估（结构化输出：`ImpactAssessorOutput`）
- `expert_supervisor`：主管裁决/整合（结构化输出：`SupervisorOutput` 或纯文本）
- `expert_council`：四阶段委员会流程（独立分析→交叉评审→共识讨论→主席定稿）

结构化输出通过 `model.with_structured_output(PydanticModel)` 实现（见 `src/agent/subagents/base.py`）。

### 4.4 专家委员会（Expert Council）怎么用才值回票价？

`expert_council` 的价值在于：**把“专家输出”变成“可互相质检、可裁决的共识结论”**。

- 交叉评审矩阵与提示模板：`src/agent/council/matrix.py`
- 执行器封装：`src/agent/subagents/council.py`

建议策略（成本/质量平衡）：
- 对 **重点 3–6 条新闻** 默认开 `expert_council`
- 对“内容简单 + 一手 A 级来源 + 用户只要速览”的条目，可只跑 `summarizer`/`impact_assessor`，必要时再 `expert_supervisor` 整合

## 5. 配置与模型路由（OpenAI / Azure / Gemini）

配置入口：`src/config.py:load_settings()`。

### 5.1 必备环境变量

- `TAVILY_API_KEY`：搜索必需
- 其一：
  - `OPENAI_API_KEY`
  - 或 Azure 三件套：`AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT_NAME`

### 5.2 可选：专家使用 Gemini

若同时提供：
- `GEMINI_KEY`
- `MODEL_GEMINI_3_FLASH`（Gemini 模型名）

则 **专家角色** 会切到 Google provider，Master 仍走 OpenAI/Azure（见 `src/config.py:default_model_map`）。

### 5.3 文件系统根目录

- `NEWS_AGENT_FS_BASE`：默认 `./data`
- CLI `--checkpoint` 会把 SQLite checkpoint 放到 `<NEWS_AGENT_FS_BASE>/checkpoints/agent_state.db`（可用 `--checkpoint-dir` 覆盖）

## 6. 运行与产物

### 6.1 CLI

```bash
uv run python -m cli.main "今天AI领域有什么进展"

# 输出到文件（Markdown）
uv run python -m cli.main --output ./reports/today.md "最新科技新闻"

# trace：终端实时可视化 + 导出 HTML/JSON
uv run python -m cli.main --trace --trace-output ./reports/trace.html "分析 Sora 最新更新"

# checkpoint：同一 thread_id 续跑/复用状态
uv run python -m cli.main --checkpoint --thread-id daily-ai "今天AI领域有什么进展"
```

注意：`cli/main.py` 里 `--model` 当前属于预留参数，尚未真正注入模型构造逻辑。

### 6.2 Python API

```python
from src.agent import create_news_agent, create_news_agent_with_checkpointing

agent = create_news_agent()
result = agent.invoke({"messages": [{"role": "user", "content": "分析今天AI热点"}]})
print(result["messages"][-1].content)

agent_ckpt = create_news_agent_with_checkpointing(thread_id="daily-ai")
result = agent_ckpt.invoke({"messages": [{"role": "user", "content": "复盘昨日科技要闻"}]})
```

## 7. 扩展开发：从哪里下手最稳

### 7.1 新增工具（search/scrape/evaluate 之外的能力）

1. 在 `src/tools/` 新增模块与 `@tool` 函数
2. 在 `src/tools/__init__.py` 导出
3. 在 `src/agent/master.py:create_news_agent()` 的 tools 列表注册

### 7.2 新增专家子 Agent

1. `src/prompts/experts.py` 添加该角色 prompt（建议同时提供 structured 版本）
2. `src/schemas/outputs.py` 添加结构化输出模型（Pydantic）
3. `src/agent/subagents/` 增加创建函数并在 `get_subagent_configs()` 注册
4. 在 `src/prompts/master.py` 更新“可用专家/协作策略”描述（让 Master 知道何时该用它）

### 7.3 调整报告深度（你最在意的部分）

报告的“长/短、深/浅”主要由 `src/prompts/master.py` 的报告模板与质量红线约束。

如果你想更稳地提升深度，优先级一般是：
1. **提升输入证据质量**：多轮搜索 + `fetch_page` 拉全文 + 交叉来源
2. **强制结构化证据链**：要求事实清单、来源链接、分歧与置信度
3. **对重点条目默认开 council**：让互评与裁决逼出更扎实的论证

## 8. 测试与质量保障

- 快速：`uv run pytest tests/ -v`
- 集成（真实 keys）：`uv run pytest tests/ -v --run-integration`
- 约定：缺少 API key 的用例会被 `skip_if_no_api_key` 跳过（见 `tests/`）

---

## 9. 文档导航

- `README.md`：快速开始与使用方式
- `docs/reference/AGENT_FLOW.md`：端到端运行流程（面向贡献者）
- `docs/EXPERT_COUNCIL_DESIGN.md`：委员会机制设计
- `docs/reference/DATETIME_CONTEXT.md`：时间上下文注入规则
- `docs/archive/`：历史阶段/旧设计文档（可能过时）

