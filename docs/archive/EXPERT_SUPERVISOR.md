# 专家主管 (Expert Supervisor)

## 概述

你的观察非常深刻！在多专家协作系统中，确实需要一个**专家主管**角色来：
1. 审核各专家的分析结果
2. 发现矛盾、错误或遗漏
3. 协调专家之间的讨论
4. 要求专家修正问题
5. 最终确认整合结果

这相当于一个**总编辑**或**质量总监**，是质量保证的关键环节。

## 为什么需要专家主管？

### 问题场景

#### 场景 1：事实矛盾
```
summarizer: "公司融资 1 亿美元"
fact_checker: "经核实，融资 5000 万美元"
→ 矛盾！需要协调
```

#### 场景 2：逻辑问题
```
fact_checker: "该消息未经证实，可能是谣言"
impact_assessor: "基于该消息，预测市场将大涨"
→ 逻辑不一致！不能基于未证实的消息做预测
```

#### 场景 3：信息缺失
```
summarizer: "公司发布新产品"
researcher: (没有提供公司背景)
impact_assessor: (没有对比竞品)
→ 背景信息不足，分析不够全面
```

#### 场景 4：分析肤浅
```
impact_assessor: "这个产品很好，会有积极影响"
→ 太笼统！需要具体分析技术、市场、用户等多个维度
```

### 解决方案：expert_supervisor

`expert_supervisor` 作为最后一道质量关卡：
- ✅ 审核所有专家的输出
- ✅ 发现并标记问题
- ✅ 协调专家修正
- ✅ 确认整合指导
- ✅ 批准最终输出

## 工作流程

### 原workflow（无主管）
```
用户输入
  ↓
query_planner 规划查询
  ↓
执行搜索
  ↓
筛选内容
  ↓
派生 4 个专家并行分析：
  ├─ summarizer
  ├─ fact_checker
  ├─ researcher
  └─ impact_assessor
  ↓
MasterAgent 直接整合结果  ❌ 问题：可能有矛盾、错误
  ↓
生成报告
```

### 新workflow（有主管）
```
用户输入
  ↓
query_planner 规划查询
  ↓
执行搜索
  ↓
筛选内容
  ↓
派生 4 个专家并行分析：
  ├─ summarizer     → /analysis/summarizer/result.md
  ├─ fact_checker   → /analysis/fact_checker/result.md
  ├─ researcher     → /analysis/researcher/result.md
  └─ impact_assessor → /analysis/impact_assessor/result.md
  ↓
【新增】派生 expert_supervisor 审核
  task("expert_supervisor", "审核各专家分析结果")
  ↓
  expert_supervisor 读取所有结果，执行检查清单：
  ✓ 事实一致性
  ✓ 逻辑完整性
  ✓ 信息准确性
  ✓ 分析深度
  ↓
  如果发现问题：
    ├─ 写入 /analysis/supervisor/issues.md
    ├─ 写入 /analysis/supervisor/discussion.md
    ├─ 写入 /analysis/supervisor/revision_requests.json
    ↓
    MasterAgent 读取问题清单
    ↓
    协调相关专家修正：
    ├─ task("fact_checker", "重新核查融资金额")
    └─ task("researcher", "补充公司背景")
    ↓
    再次调用 expert_supervisor 审核
    ↓
    重复直到审核通过
  ↓
  如果审核通过：
    ├─ 写入 /analysis/supervisor/approval.md
    └─ 写入 /analysis/supervisor/integration_guide.md
  ↓
MasterAgent 根据整合指导生成报告 ✅ 质量有保证
  ↓
最终输出
```

## expert_supervisor 的职责

### 1. 质量审核

#### 一致性检查
- **事实一致性**：不同专家的数字、日期、人物是否一致？
- **逻辑一致性**：结论是否自洽？
- **时间一致性**：事件时间线是否清晰？

#### 完整性检查
- **信息完整性**：是否遗漏重要信息？
- **分析完整性**：是否遗漏重要角度？
- **来源完整性**：关键声明是否都有来源？

#### 准确性检查
- **事实准确性**：关键事实是否经过验证？
- **表述准确性**：是否有模糊或误导性表述？
- **归因准确性**：因果关系是否有依据？

#### 深度检查
- **分析深度**：是否深入本质？
- **洞察质量**：是否有独到见解？

### 2. 问题协调

发现问题时：
1. **记录问题** → `/analysis/supervisor/issues.md`
2. **组织讨论** → `/analysis/supervisor/discussion.md`
3. **要求修正** → `/analysis/supervisor/revision_requests.json`
4. **等待修正** → MasterAgent 协调专家
5. **重新审核** → 再次检查

### 3. 整合指导

审核通过后：
1. **编写审核意见** → `/analysis/supervisor/approval.md`
2. **提供整合指导** → `/analysis/supervisor/integration_guide.md`
   - 推荐的报告结构
   - 需要重点突出的内容
   - 需要注意的风险提示

## 示例：审核发现问题

### Issues.md
```markdown
## 发现的问题

### 问题 1: 事实矛盾 [严重性：高]
- **位置**: summarizer vs fact_checker
- **描述**: 融资金额不一致（summarizer 说 1 亿，fact_checker 说 5000 万）
- **要求**: fact_checker 重新核查，summarizer 同步更新

### 问题 2: 信息缺失 [严重性：中]
- **位置**: researcher
- **描述**: 未提供公司背景和历史融资情况
- **要求**: 补充完整的公司背景信息

### 问题 3: 逻辑问题 [严重性：高]
- **位置**: impact_assessor
- **描述**: 基于未经证实的消息做影响预测，逻辑不严谨
- **要求**: 在预测中明确标注"假设该消息属实"或重新调整分析
```

### Discussion.md
```markdown
## 专家讨论

### 话题 1: 融资金额确认

@fact_checker @summarizer

请核对原文并确认准确金额。fact_checker，你的来源是什么？

### 话题 2: 公司背景补充

@researcher

分析需要更多背景支持，请补充：
1. 公司成立时间和主要业务
2. 历史融资轮次（A轮、B轮等）
3. 主要竞争对手和市场地位
```

### Revision_requests.json
```json
{
  "revisions": [
    {
      "expert": "fact_checker",
      "issue": "融资金额不一致",
      "action": "重新核查并确认准确金额，提供核查来源",
      "priority": "high"
    },
    {
      "expert": "researcher",
      "issue": "缺少公司背景",
      "action": "补充完整的公司背景信息（成立时间、业务、历史融资）",
      "priority": "medium"
    },
    {
      "expert": "impact_assessor",
      "issue": "基于未证实信息做预测",
      "action": "在分析中明确标注前提条件或调整分析逻辑",
      "priority": "high"
    }
  ]
}
```

## 示例：审核通过

### Approval.md
```markdown
## 审核结果：通过

### 整体评价
各专家的分析已达到发布标准：
- ✅ 事实准确，所有关键数据已验证
- ✅ 逻辑清晰，结论有依据
- ✅ 信息完整，背景充分
- ✅ 分析深入，有独到洞察

### 关键发现
1. 公司B轮融资5000万美元，估值达到5亿美元
2. 该融资将主要用于产品研发和市场扩张
3. 竞争格局变化：本次融资后有望成为行业前三

### 建议强调
在最终报告中建议强调：
- fact_checker 核实的准确融资金额
- researcher 提供的市场竞争分析
- impact_assessor 对行业格局的洞察

### 风险提示
需要在报告中提示：
- 市场环境不确定性
- 竞品可能的应对策略
```

### Integration_guide.md
```markdown
## 整合指导

### 推荐结构
1. **融资概述**（来自 summarizer）
   - 金额、估值、投资方
2. **公司背景**（来自 researcher）
   - 业务、历史、竞争地位
3. **事实核查**（来自 fact_checker）
   - 强调已验证的关键信息
4. **影响分析**（来自 impact_assessor）
   - 对行业、竞争格局的影响

### 重点突出
- **首段**：直接给出核实的融资金额和估值
- **中段**：补充公司背景，让读者了解context
- **末段**：分析影响，给出有价值的洞察

### 语气与风格
- 保持客观、专业
- 对已验证的事实使用肯定语气
- 对推测使用谨慎表述（"可能"、"预计"）

### 注意事项
- 所有关键数据都已验证，可以直接引用
- 时间线已核对，无矛盾
- 专家间的观点一致，可以综合呈现
```

## 配置信息

### Model
- 使用与 MasterAgent 相同的强模型（`gpt-4o`）
- 需要强大的判断力和逻辑推理能力

### Tools
- 无需外部工具
- 可以通过 MasterAgent 的 `task()` 调用其他专家

### Position
- 在 subagents 列表的最后位置
- 在所有分析专家之后调用

## 测试覆盖

新增测试：10 个
- ✅ 配置验证
- ✅ 提示词内容检查
- ✅ 质量检查清单
- ✅ 输出格式定义
- ✅ 典型场景覆盖
- ✅ 工作流程集成

总计测试：**71 个**
- 60 passed
- 11 skipped（需要 API keys）

## 文件结构

### 配置文件
- `src/agent/subagents.py` - 添加 `expert_supervisor` 配置和 `EXPERT_SUPERVISOR_PROMPT`

### 测试文件
- `tests/agent/test_supervisor.py` - 专门测试 supervisor
- `tests/agent/test_subagents.py` - 更新为 6 个专家

### 文档
- `EXPERT_SUPERVISOR.md` - 本文档
- `IMPLEMENTATION_PLAN.md` - 更新 Phase 4 任务

## 使用指南

### MasterAgent 如何使用

```python
# 1. 派生分析专家
task("summarizer", ...)
task("fact_checker", ...)
task("researcher", ...)
task("impact_assessor", ...)

# 2. 等待所有专家完成

# 3. 派生专家主管审核
task("expert_supervisor", "审核各专家分析结果")

# 4. 读取审核结果
result = read_file("/analysis/supervisor/approval.md")

# 5a. 如果审核通过
if "审核结果：通过" in result:
    # 读取整合指导
    guide = read_file("/analysis/supervisor/integration_guide.md")
    # 根据指导生成报告
    
# 5b. 如果需要修正
if "审核结果：需要修正" in result:
    # 读取问题清单
    issues = read_file("/analysis/supervisor/issues.md")
    revisions = read_file("/analysis/supervisor/revision_requests.json")
    # 协调专家修正
    # 重新审核
```

## 价值

1. **质量保证**：多一道审核关卡，确保输出质量
2. **发现问题**：自动发现专家间的矛盾和遗漏
3. **协调机制**：提供专家间讨论和修正的流程
4. **整合指导**：为最终报告生成提供明确指导
5. **可追溯性**：所有审核意见都有记录

expert_supervisor 是确保多专家协作系统输出高质量内容的关键！

