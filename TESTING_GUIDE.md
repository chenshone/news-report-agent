# 测试指南

## 测试策略

本项目采用**真实集成测试**策略，而非 mock 数据测试。这确保了代码在实际使用环境中的正确性。

### 测试类型

#### 1. 单元测试 (Unit Tests)
- 测试独立的函数和数据模型
- 不需要外部 API
- 例如：`test_models.py`, `test_config.py` (部分)

#### 2. 集成测试 (Integration Tests)
- 测试组件之间的集成
- **使用真实的 API keys**
- 如果 API keys 未配置，测试将被跳过（skip）

### 为什么不使用 Mock 数据？

在涉及以下情况时，mock 数据测试是不够的：

1. **LangChain/DeepAgents 集成**
   - LLM 模型初始化（`ChatOpenAI`, `AzureChatOpenAI`）
   - Agent 创建和配置
   - Tool 注册和调用

2. **外部 API 调用**
   - Tavily 搜索
   - 网页抓取
   - LLM 推理

**原因**：
- Mock 数据无法验证真实的 API 行为
- 参数传递、类型转换等问题只能在真实环境中发现
- Agent 的实际表现只能通过真实调用来验证

## 配置测试环境

### 1. 设置 API Keys

复制 `.env.example` 为 `.env` 并填入真实的 API keys：

```bash
cp env.example .env
```

编辑 `.env`：

```bash
# OpenAI (推荐用于测试)
OPENAI_API_KEY=sk-xxx

# 或者 Azure OpenAI
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Tavily (必需)
TAVILY_API_KEY=tvly-xxx
```

### 2. 运行测试

```bash
# 运行所有测试（会跳过需要 API keys 的测试）
uv run pytest tests/ -v

# 查看跳过的测试原因
uv run pytest tests/ -v -rs

# 运行特定模块的测试
uv run pytest tests/agent/ -v

# 运行单个测试
uv run pytest tests/agent/test_master.py::test_create_news_agent_basic -v
```

### 3. 测试输出

**无 API keys**：
```
SKIPPED [1] No valid LLM API key configured...
```

**有 API keys**：
```
PASSED - 测试通过，agent 创建成功并能正常调用
```

## 测试注意事项

### 成本控制

1. **使用轻量级模型**
   - 测试中使用 `gpt-4o-mini` 而非 `gpt-4o`
   - 降低每次测试的成本

2. **简短的测试查询**
   - 使用简单的问题："你好"、"1+1=?"
   - 避免复杂的多轮对话

3. **温度设置**
   - 大部分测试使用 `temperature=0.0` 确保确定性
   - 减少不必要的随机性和成本

### 测试隔离

每个测试：
- 独立创建 agent 实例
- 使用独立的配置
- 不共享状态

### 跳过机制

`skip_if_no_api_key` fixture 会检查：
- ✅ `OPENAI_API_KEY` 或完整的 Azure 配置
- ✅ `TAVILY_API_KEY`
- ❌ Placeholder 值 (以 `YOUR_` 开头)

## 添加新测试

### 集成测试模板

```python
def test_new_feature(skip_if_no_api_key):
    """Integration test: describe what this tests."""
    from src.agent import create_news_agent
    from src.config import load_settings, create_chat_model, ModelConfig
    
    # Load real config
    config = load_settings()
    model_config = ModelConfig(
        model="gpt-4o-mini",
        provider=config.model_map["master"].provider,
        temperature=0.0
    )
    model = create_chat_model(model_config, config)
    
    # Create agent
    agent = create_news_agent(model_override=model)
    
    # Test with minimal query
    result = agent.invoke({
        "messages": [{"role": "user", "content": "简单测试"}]
    })
    
    # Assertions
    assert result is not None
    assert "messages" in result
```

### 单元测试模板

```python
def test_data_model():
    """Unit test: describe what this tests."""
    from src.schemas import NewsItem
    
    # No API calls needed
    item = NewsItem(
        title="Test",
        url="https://example.com",
        published_at="2024-01-01T00:00:00Z"
    )
    
    assert item.title == "Test"
```

## CI/CD 集成

### GitHub Actions 配置示例

```yaml
- name: Run tests with API keys
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
  run: |
    uv run pytest tests/ -v --tb=short
```

### 无 API keys 的 CI

如果 CI 环境没有配置 API keys：
- 所有集成测试将被跳过
- 只运行单元测试
- 仍然能验证代码结构和基本逻辑

## 调试测试

### 查看详细输出

```bash
# 显示 print 输出
uv run pytest tests/agent/ -v -s

# 显示完整的错误堆栈
uv run pytest tests/agent/ -v --tb=long

# 在第一个失败处停止
uv run pytest tests/agent/ -v -x
```

### 查看跳过的测试

```bash
# 显示跳过原因
uv run pytest tests/ -v -rs
```

## 测试覆盖率

当前测试覆盖：
- ✅ 配置加载和验证
- ✅ 数据模型序列化
- ✅ 自定义工具（搜索、抓取、评估）
- ✅ Agent 创建和配置
- ✅ Agent 基本调用
- ⏳ 完整的工作流程（Phase 4-5）

## 最佳实践

1. **先写单元测试，再写集成测试**
   - 单元测试快速验证基本逻辑
   - 集成测试验证实际行为

2. **保持测试简洁**
   - 每个测试只验证一个功能点
   - 使用清晰的测试名称

3. **真实环境测试**
   - 定期在真实 API keys 下运行测试
   - 发现 mock 测试无法捕获的问题

4. **成本意识**
   - 使用最便宜的模型
   - 保持测试查询简短
   - 避免不必要的重复调用

