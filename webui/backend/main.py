"""FastAPI Backend for News Report Agent Web UI

Provides REST API endpoints with SSE streaming for real-time agent progress.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Add project root and backend dir to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

# Import SSE handler
from sse_handler import SSECallbackHandler, SSEEventType, SSEEvent


# ============================================================================
# Models
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request body for analyze endpoint"""
    query: str
    domain: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response for analyze endpoint"""
    task_id: str
    message: str


class TaskStatus(BaseModel):
    """Task status response"""
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    report_html: Optional[str] = None
    error: Optional[str] = None


# New models for confirmation flow
class PrepareRequest(BaseModel):
    """Request for prepare analysis (Phase 1: understanding)"""
    query: str
    domain: Optional[str] = None


class SearchDirectionResponse(BaseModel):
    """A search direction in the plan"""
    source: str
    query_template: str
    purpose: str
    priority: str


class IntentAnalysisResponse(BaseModel):
    """Simplified intent analysis for frontend display"""
    original_query: str
    understood_query: str
    time_range_description: str
    time_range_days: int
    domain_keywords: list[str]
    domain_category: str
    possible_interests: list[str]
    suggested_depth: str
    estimated_time_minutes: int
    clarification_questions: list[str]


class SearchPlanResponse(BaseModel):
    """Response containing the search plan for user confirmation"""
    task_id: str
    intent: IntentAnalysisResponse
    included_directions: list[SearchDirectionResponse]
    excluded_directions: list[str]
    total_estimated_queries: int
    estimated_time_minutes: int


class UserConfirmationRequest(BaseModel):
    """User confirmation with adjustments"""
    task_id: str
    approved: bool
    selected_interests: list[str] = []
    excluded_topics: list[str] = []
    depth_preference: str = "deep"
    additional_context: str = ""


class ExecuteRequest(BaseModel):
    """Request to execute an already-prepared analysis"""
    task_id: str
    confirmation: UserConfirmationRequest


# ============================================================================
# Task Storage (in-memory for single-user mode)
# ============================================================================

class TaskStore:
    """Simple in-memory task storage"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.event_queues: Dict[str, asyncio.Queue] = {}
    
    def create_task(self, task_id: str, query: str, domain: Optional[str] = None):
        self.tasks[task_id] = {
            "status": "pending",
            "query": query,
            "domain": domain,
            "report_html": None,
            "report_markdown": None,
            "error": None,
            "created_at": datetime.now(),
        }
        self.event_queues[task_id] = asyncio.Queue(maxsize=1000)
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)
    
    def get_queue(self, task_id: str) -> Optional[asyncio.Queue]:
        return self.event_queues.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)


task_store = TaskStore()


# ============================================================================
# FastAPI App
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 News Report Agent Web UI Backend starting...")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="News Report Agent Web UI",
    description="Web interface for the news report agent with streaming support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "news-report-agent-webui"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def start_analysis(request: AnalyzeRequest):
    """
    Start a new analysis task (quick mode - no confirmation).
    
    Returns a task_id that can be used to stream events and get the final report.
    """
    task_id = str(uuid.uuid4())[:8]
    task_store.create_task(task_id, request.query, request.domain)
    
    # Start background task
    asyncio.create_task(_run_agent_task(task_id, request.query, request.domain))
    
    return AnalyzeResponse(
        task_id=task_id,
        message="Analysis started. Connect to /api/stream/{task_id} for real-time updates."
    )


@app.post("/api/analyze/prepare", response_model=SearchPlanResponse)
async def prepare_analysis(request: PrepareRequest):
    """
    Prepare analysis - Phase 1: Understanding.
    
    Analyzes user query and returns a search plan for confirmation.
    User can then call /api/analyze/execute with modifications.
    """
    task_id = str(uuid.uuid4())[:8]
    
    try:
        # Import and run intent analyzer
        from src.config import load_settings
        from src.agent.subagents.intent_analyzer import create_intent_analyzer
        from src.agent.subagents.search_plan_generator import create_search_plan_generator
        
        config = load_settings()
        
        # Run intent analyzer synchronously (fast operation)
        # The structured runnable expects {"messages": [...]} format
        loop = asyncio.get_event_loop()
        
        intent_analyzer = create_intent_analyzer(config)
        intent_input = {"messages": [{"role": "user", "content": request.query}]}
        intent_output = await loop.run_in_executor(
            None,
            lambda: intent_analyzer['runnable'].invoke(intent_input)
        )
        
        # Parse the JSON output from the last message
        import json
        last_msg_content = intent_output["messages"][-1].content
        intent_data = json.loads(last_msg_content)
        
        # Run search plan generator
        search_plan_gen = create_search_plan_generator(config)
        
        # Pass the intent analysis to search plan generator
        plan_input_text = f"""用户查询: {request.query}

意图分析结果:
- 理解的意图: {intent_data['understood_query']}
- 时间范围: {intent_data['time_range_description']} ({intent_data['time_range_days']} 天)
- 领域关键词: {', '.join(intent_data['domain_keywords'])}
- 领域分类: {intent_data['domain_category']}
- 可能关注点: {', '.join(intent_data['possible_interests'])}
- 建议深度: {intent_data['suggested_depth']}

请基于以上意图分析生成搜索计划。"""

        plan_input = {"messages": [{"role": "user", "content": plan_input_text}]}
        plan_output = await loop.run_in_executor(
            None,
            lambda: search_plan_gen['runnable'].invoke(plan_input)
        )
        
        # Parse the JSON output
        last_plan_msg = plan_output["messages"][-1].content
        plan_data = json.loads(last_plan_msg)
        
        # Store the plan for later execution
        task_store.tasks[task_id] = {
            "status": "prepared",
            "query": request.query,
            "domain": request.domain,
            "intent": intent_data,
            "search_plan": plan_data,
            "created_at": datetime.now(),
        }
        
        # Convert to response models
        intent_response = IntentAnalysisResponse(
            original_query=intent_data.get('original_query', request.query),
            understood_query=intent_data['understood_query'],
            time_range_description=intent_data['time_range_description'],
            time_range_days=intent_data['time_range_days'],
            domain_keywords=intent_data['domain_keywords'],
            domain_category=intent_data['domain_category'],
            possible_interests=intent_data['possible_interests'],
            suggested_depth=intent_data['suggested_depth'],
            estimated_time_minutes=intent_data.get('estimated_time_minutes', 15),
            clarification_questions=intent_data.get('clarification_questions', []),
        )
        
        directions_response = [
            SearchDirectionResponse(
                source=d['source'],
                query_template=d['query_template'],
                purpose=d['purpose'],
                priority=d['priority'],
            )
            for d in plan_data.get('included_directions', [])
        ]
        
        return SearchPlanResponse(
            task_id=task_id,
            intent=intent_response,
            included_directions=directions_response,
            excluded_directions=plan_data.get('excluded_directions', []),
            total_estimated_queries=plan_data.get('total_estimated_queries', len(directions_response)),
            estimated_time_minutes=plan_data.get('estimated_time_minutes', 15),
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to prepare analysis: {str(e)}")


@app.post("/api/analyze/execute", response_model=AnalyzeResponse)
async def execute_analysis(request: ExecuteRequest):
    """
    Execute analysis - Phase 2: Execution with confirmation.
    
    Takes the user's confirmation and executes the search plan.
    """
    task_id = request.task_id
    task = task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found. Please call /api/analyze/prepare first.")
    
    if task.get("status") != "prepared":
        raise HTTPException(status_code=400, detail="Task is not in prepared state.")
    
    # Store user confirmation
    task_store.update_task(task_id, user_confirmation=request.confirmation)
    
    # Create event queue for this task
    task_store.event_queues[task_id] = asyncio.Queue(maxsize=1000)
    
    # Build modified query with user preferences
    original_query = task["query"]
    confirmation = request.confirmation
    
    # Enhance query with user context
    enhanced_parts = [original_query]
    if confirmation.excluded_topics:
        enhanced_parts.append(f"\n\n排除以下已知内容: {', '.join(confirmation.excluded_topics)}")
    if confirmation.selected_interests:
        enhanced_parts.append(f"\n\n重点关注: {', '.join(confirmation.selected_interests)}")
    if confirmation.additional_context:
        enhanced_parts.append(f"\n\n用户补充: {confirmation.additional_context}")
    
    enhanced_query = "".join(enhanced_parts)
    
    # Start background task with enhanced query
    asyncio.create_task(_run_agent_task(
        task_id, 
        enhanced_query, 
        task.get("domain"),
        depth=confirmation.depth_preference
    ))
    
    return AnalyzeResponse(
        task_id=task_id,
        message="Execution started. Connect to /api/stream/{task_id} for real-time updates."
    )


@app.get("/api/stream/{task_id}")
async def stream_events(task_id: str):
    """
    SSE endpoint for streaming agent events.
    
    Events are formatted as:
    - type: event type (llm_start, tool_start, etc.)
    - name: display name
    - detail: additional information
    - timestamp: event time
    """
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    queue = task_store.get_queue(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Event queue not found")
    
    async def event_generator():
        while True:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(queue.get(), timeout=300)
                
                if isinstance(event, SSEEvent):
                    yield {
                        "event": "message",
                        "data": event.to_sse_data()
                    }
                    
                    # Check for completion events
                    if event.event_type == SSEEventType.REPORT:
                        break
                    if event.event_type == SSEEventType.ERROR and not task_store.get_task(task_id).get("status") == "running":
                        break
                elif event is None:
                    # Sentinel value for completion
                    break
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"event": "ping", "data": "keepalive"}
    
    return EventSourceResponse(event_generator())


@app.get("/api/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get task status and report if completed"""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        report_html=task.get("report_html"),
        error=task.get("error"),
    )


@app.get("/api/report/{task_id}", response_class=HTMLResponse)
async def get_report(task_id: str):
    """Get the final HTML report"""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report not ready yet")
    
    report_html = task.get("report_html", "")
    if not report_html:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report_html


# ============================================================================
# Background Task Execution
# ============================================================================

async def _run_agent_task(
    task_id: str, 
    query: str, 
    domain: Optional[str] = None,
    depth: str = "deep",
):
    """Run the agent in background and stream events.
    
    Args:
        task_id: Unique task identifier.
        query: User query (may be enhanced with user preferences).
        domain: Optional domain filter.
        depth: Analysis depth - "quick" for faster analysis, "deep" for thorough.
    """
    queue = task_store.get_queue(task_id)
    if not queue:
        return
    
    task_store.update_task(task_id, status="running")
    
    # Send start event
    await queue.put(SSEEvent(
        event_type=SSEEventType.AGENT_START,
        name="🚀 分析开始",
        detail=f"正在分析: {query}",
    ))
    
    try:
        # Import agent modules
        from src.agent import create_news_agent
        from src.utils.templates import format_simple_output
        
        # Build full query with domain if provided
        full_query = query
        if domain:
            full_query = f"[领域: {domain}] {query}"
        
        # Create callback handler
        callback = SSECallbackHandler(queue)
        
        # Create agent (no callbacks parameter here)
        agent = create_news_agent()
        
        # Run agent with callbacks in invoke config (following CLI pattern)
        # Note: LangChain callbacks are passed via config, not agent creation
        invoke_config = {"callbacks": [callback]}
        
        # Run agent (this is synchronous, run in executor)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent.invoke(
                {"messages": [{"role": "user", "content": full_query}]},
                config=invoke_config,
            )
        )
        
        # Extract report content
        report_markdown = format_simple_output(result)
        report_html = _markdown_to_html(report_markdown, query)
        
        # Store results
        task_store.update_task(
            task_id,
            status="completed",
            report_markdown=report_markdown,
            report_html=report_html,
        )
        
        # Send completion event with report
        await queue.put(SSEEvent(
            event_type=SSEEventType.REPORT,
            name="📋 报告生成完成",
            detail="分析完成，报告已生成",
            data={"report_html": report_html},
        ))
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        
        task_store.update_task(task_id, status="error", error=error_msg)
        
        await queue.put(SSEEvent(
            event_type=SSEEventType.ERROR,
            name="❌ 分析失败",
            error=error_msg,
        ))
    
    # Send sentinel to close stream
    await queue.put(None)


def _markdown_to_html(markdown_content: str, query: str) -> str:
    """Convert Markdown report to styled HTML"""
    import re
    
    # Simple markdown to HTML conversion
    html_content = markdown_content
    
    # Headers
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    
    # Bold and italic
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
    
    # Links
    html_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html_content)
    
    # Lists
    html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html_content)
    
    # Paragraphs
    paragraphs = html_content.split('\n\n')
    processed = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<h') and not p.startswith('<ul') and not p.startswith('<li'):
            p = f'<p>{p}</p>'
        processed.append(p)
    html_content = '\n'.join(processed)
    
    # Wrap in styled container
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>热点资讯分析报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1d1d1f;
            background: linear-gradient(180deg, #f5f5f7 0%, #ffffff 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        .report-container {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            padding: 48px;
        }}
        
        .report-header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid #e5e5e7;
        }}
        
        .report-header h1 {{
            font-size: 32px;
            font-weight: 600;
            color: #1d1d1f;
            letter-spacing: -0.5px;
            margin-bottom: 16px;
        }}
        
        .report-meta {{
            font-size: 14px;
            color: #86868b;
        }}
        
        .report-meta .query {{
            background: linear-gradient(90deg, #0071e3, #42a5f5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 500;
        }}
        
        .report-content {{
            font-size: 16px;
            line-height: 1.8;
        }}
        
        .report-content h1 {{
            font-size: 28px;
            font-weight: 600;
            margin: 32px 0 16px 0;
            color: #1d1d1f;
        }}
        
        .report-content h2 {{
            font-size: 22px;
            font-weight: 600;
            margin: 28px 0 14px 0;
            color: #1d1d1f;
        }}
        
        .report-content h3 {{
            font-size: 18px;
            font-weight: 600;
            margin: 24px 0 12px 0;
            color: #1d1d1f;
        }}
        
        .report-content p {{
            margin-bottom: 16px;
            color: #424245;
        }}
        
        .report-content ul {{
            margin: 16px 0;
            padding-left: 24px;
        }}
        
        .report-content li {{
            margin-bottom: 8px;
            color: #424245;
        }}
        
        .report-content a {{
            color: #0071e3;
            text-decoration: none;
            transition: opacity 0.2s;
        }}
        
        .report-content a:hover {{
            opacity: 0.7;
        }}
        
        .report-content strong {{
            font-weight: 600;
            color: #1d1d1f;
        }}
        
        .report-footer {{
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid #e5e5e7;
            text-align: center;
            font-size: 13px;
            color: #86868b;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .report-container {{
                box-shadow: none;
                border-radius: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1>📰 热点资讯分析报告</h1>
            <div class="report-meta">
                <p>查询: <span class="query">{query}</span></p>
                <p>生成时间: {now}</p>
            </div>
        </div>
        <div class="report-content">
            {html_content}
        </div>
        <div class="report-footer">
            <p>本报告由 AI Agent 自动生成</p>
        </div>
    </div>
</body>
</html>"""


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
