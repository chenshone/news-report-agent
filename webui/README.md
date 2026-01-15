# News Report Agent Web UI

基于 React + FastAPI 的热点资讯分析 Web 界面。

## 项目结构

```
webui/
├── backend/          # FastAPI 后端
│   ├── main.py       # API 入口
│   ├── sse_handler.py # SSE 回调处理
│   └── requirements.txt
└── frontend/         # React 前端
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   └── styles/
    └── package.json
```

## 快速开始

### 1. 启动后端

```bash
cd webui/backend
pip install -r requirements.txt
python main.py
# 或者使用 uvicorn
# uvicorn main:app --reload --port 8000
```

后端运行在 http://localhost:8000

### 2. 启动前端

```bash
cd webui/frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173

### 3. 使用

1. 打开 http://localhost:5173
2. 在输入框中输入您想了解的话题，如"今天AI领域有什么进展"
3. 点击"开始分析"按钮
4. 实时查看分析进度
5. 查看最终报告，可下载 PDF

## 功能

- ✅ Apple 风格简洁设计
- ✅ 实时流式展示 Agent 工作进度
- ✅ HTML 报告渲染
- ✅ PDF 下载支持
- ✅ 响应式布局

## API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/analyze` | POST | 开始分析任务 |
| `/api/stream/{task_id}` | GET | SSE 流式事件 |
| `/api/task/{task_id}` | GET | 获取任务状态 |
| `/api/report/{task_id}` | GET | 获取 HTML 报告 |
