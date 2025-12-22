# 日期时间上下文注入

## 概述

为了让 `query_planner` 生成更精确的搜索查询，系统会自动将当前日期时间信息注入到 MasterAgent 的系统提示词中。

## 实现机制

### 1. 时间注入点

在 `create_news_agent()` 函数中：

```python
from datetime import datetime

agent = create_news_agent(
    current_datetime=datetime.now()  # 默认使用当前时间
)
```

### 2. 时间信息格式

系统会将日期时间格式化为中文友好的格式：

```
当前日期：2024年12月15日 (星期日)
当前时间：14:30:00

时间参考：
- "今天" 指的是 2024年12月15日
- "昨天" 指的是 2024年12月14日
- "近期" 通常指最近 7 天左右
- "最新" 通常指最近 24-48 小时
```

### 3. 注入到系统提示词

时间信息会被自动添加到 MasterAgent 的系统提示词末尾：

```python
enhanced_system_prompt = f"""{MASTER_AGENT_SYSTEM_PROMPT}

## 当前日期时间信息

{datetime_info}

**重要提示**：
- 当用户提到"今天"、"近期"、"最新"等时间词时，参考上述日期时间
- 将这个信息传递给 query_planner，让它生成带时间限定的查询
- 例如：用户说"今天AI进展" → query_planner 应生成 "AI 2024年12月15日 最新进展"
"""
```

## query_planner 的时间意识

### 提示词更新

`query_planner` 的提示词已更新，强调时间精确性：

```python
查询设计原则：
- **时间精确**：根据 MasterAgent 提供的当前日期生成查询
  - 用户说"今天" → 使用当前日期 "YYYY年MM月DD日" 或 "YYYY-MM-DD"
  - 用户说"近期" → 使用当前月份 "YYYY年MM月"
  - 用户说"最新" → 添加 "latest" "最新" "24小时内"
```

### 示例对比

#### ❌ 之前（没有时间上下文）

**用户输入**："今天 AI 领域有什么进展"

**query_planner 可能生成**：
```json
{
  "queries": [
    "AI 最新进展",  // 太模糊，搜索引擎不知道"最新"是多新
    "AI Agent 进展"  // 缺少时间限定
  ]
}
```

#### ✅ 现在（有时间上下文）

**MasterAgent 知道**：当前日期是 2024年12月15日（星期日）

**用户输入**："今天 AI 领域有什么进展"

**query_planner 生成**：
```json
{
  "queries": [
    {
      "query": "AI Agent 2024-12-15 最新进展 latest news",
      "purpose": "核心技术进展（当日）",
      "priority": "high"
    },
    {
      "query": "OpenAI ChatGPT 2024年12月15日 更新 announcement",
      "purpose": "大厂产品动态（当日）",
      "priority": "high"
    }
  ]
}
```

## 使用方式

### 默认行为（自动使用当前时间）

```python
from src.agent import create_news_agent

# 自动使用 datetime.now()
agent = create_news_agent()

result = agent.invoke({
    "messages": [{"role": "user", "content": "分析今天AI领域热点"}]
})
```

### 自定义时间（用于测试或特殊场景）

```python
from datetime import datetime
from src.agent import create_news_agent

# 指定特定时间（例如测试历史日期）
custom_time = datetime(2024, 12, 1, 10, 0, 0)
agent = create_news_agent(current_datetime=custom_time)

result = agent.invoke({
    "messages": [{"role": "user", "content": "分析今天AI领域热点"}]
})
# Agent 会认为"今天"是 2024年12月1日
```

### CLI 使用（Phase 5 实现）

```bash
# 默认使用当前时间
python -m cli.main "今天科技圈有什么大事"

# 指定时间（用于回溯分析）
python -m cli.main --date 2024-12-01 "分析这天的AI热点"
```

## 时间参考语义

系统理解以下时间词：

| 用户表述 | 系统理解 | 示例查询 |
|---------|---------|---------|
| 今天 | 当前日期 | "AI 2024-12-15 news" |
| 昨天 | 前一天 | "AI 2024-12-14 news" |
| 近期 | 最近 7 天 | "AI 2024年12月 latest" |
| 最新 | 24-48 小时 | "AI latest 24h news" |
| 本周 | 当前周 | "AI week 2024-W50" |
| 本月 | 当前月 | "AI 2024年12月" |

## 测试

### 单元测试

```python
def test_format_datetime_context():
    from src.agent.master import format_datetime_context
    
    dt = datetime(2024, 12, 15, 14, 30, 0)
    context = format_datetime_context(dt)
    
    assert "2024年12月15日" in context
    assert "星期日" in context
    assert "14:30:00" in context
```

### 集成测试

```python
def test_agent_with_datetime(skip_if_no_api_key):
    dt = datetime(2024, 12, 15, 14, 30, 0)
    agent = create_news_agent(current_datetime=dt)
    
    result = agent.invoke({
        "messages": [{"role": "user", "content": "今天是几号？"}]
    })
    
    # Agent 应该能回答正确的日期
    assert result is not None
```

## 优势

1. **查询精确性**：搜索引擎能理解具体时间范围
2. **减少歧义**："今天"不再模糊，明确对应具体日期
3. **时间相关性**：搜索结果更贴近用户实际意图
4. **可测试性**：可以模拟任意时间点进行测试
5. **可追溯性**：报告中的时间引用清晰明确

## 实现文件

- `src/agent/master.py` - `format_datetime_context()` 函数
- `src/agent/master.py` - `create_news_agent()` 时间注入逻辑
- `src/agent/subagents.py` - `query_planner` 提示词更新
- `tests/agent/test_datetime_context.py` - 相关测试

## 注意事项

1. **时区**：当前使用本地时间，未来可考虑支持时区配置
2. **格式一致性**：统一使用中文日期格式，便于 LLM 理解
3. **测试隔离**：测试时使用固定时间，避免时间依赖导致的不稳定
4. **历史分析**：通过自定义时间参数，可以分析历史时期的热点

## 未来扩展

- [ ] 支持时区配置
- [ ] 支持相对时间表达（"3天前"、"上周"）
- [ ] 智能时间范围推断（根据话题自动确定合适的时间窗口）
- [ ] 多语言日期格式支持

