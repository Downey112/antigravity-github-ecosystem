"""Cloud Run Serverless Agent Entrypoint & Mission Control API.

Exposes HTTP endpoints for:
- Web Dashboard UI (GET /)
- Cloud Run health & liveness probes (GET /health)
- Real-time Subagent Actions (/api/trigger/...)
- GitHub webhook events & triage feeds (/api/issues, /webhooks/github)
- Session metadata and transcripts (/api/sessions)
- AntigravityKit Workflows Catalog (/api/workflows)
- Interactive agent chat prompt (/api/agent/chat)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import settings
from src.runtime import AntigravityRuntime
from src.scheduler import scheduler
from src.notifications.linkgravity import linkgravity
from src.integrations.github_client import github_client
from src.subagents.dep_scanner import DependencyScannerSubagent
from src.subagents.browser_verifier import BrowserVerificationSubagent

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("CloudRunServer")

app = FastAPI(
    title="Antigravity GitHub Ecosystem Mission Control",
    version="1.0.0",
    description="Autonomous Cloud Run agent daemon with GitHub MCP and LinkGravity integrations."
)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
WORKFLOWS_PATH = settings.BASE_DIR / ".agents" / "skills" / "antigravity-kit" / "workflows.json"

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Antigravity Cloud Run Daemon...")
    # Optional: Start scheduler task in background if ALWAYS_ON is desired
    if settings.ENV == "production":
        asyncio.create_task(scheduler.start())

# -----------------------------------------------------------------------------
# Frontend Dashboard Routes
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Renders the single-page Mission Control Web Dashboard."""
    index_path = TEMPLATE_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=404)
    return HTMLResponse(index_path.read_text(encoding="utf-8"))

# -----------------------------------------------------------------------------
# System & Health Routes
# -----------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Liveness probe for Cloud Run."""
    return {
        "status": "healthy",
        "service": settings.CLOUD_RUN_SERVICE_NAME,
        "region": settings.GCP_REGION,
        "environment": settings.ENV,
        "repo": settings.GITHUB_REPOSITORY,
    }

# -----------------------------------------------------------------------------
# GitHub & Subagent API Routes
# -----------------------------------------------------------------------------

@app.get("/api/issues")
async def get_github_issues():
    """Fetches open GitHub issues and their latest comments."""
    issues = await github_client.list_open_issues()
    enriched_issues = []
    
    # Enrich issues with comments
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        for issue in issues[:10]:
            issue_num = issue.get("number")
            comments_url = f"https://api.github.com/repos/{settings.GITHUB_REPOSITORY}/issues/{issue_num}/comments"
            try:
                res = await client.get(comments_url, headers=github_client._headers())
                comments = res.json() if res.status_code == 200 else []
            except Exception:
                comments = []
            
            enriched_issues.append({
                "number": issue_num,
                "title": issue.get("title"),
                "body": issue.get("body"),
                "user": issue.get("user", {}),
                "created_at": issue.get("created_at"),
                "comments_count": len(comments),
                "comments_content": comments,
            })
            
    return enriched_issues

@app.post("/api/trigger/dep-scan")
async def trigger_dep_scan():
    """Runs dep-scanner on-demand and returns the JSON report."""
    scanner = DependencyScannerSubagent(settings.BASE_DIR)
    return scanner.run_full_scan()

@app.post("/api/trigger/browser-check")
async def trigger_browser_check(request: Request):
    """Runs browser verification against a target URL."""
    body = await request.json()
    url = body.get("url", "https://httpbin.org/status/200")
    verifier = BrowserVerificationSubagent()
    return await verifier.verify_endpoint(url)

@app.post("/api/agent/chat")
async def agent_chat(request: Request):
    """Executes an ad-hoc prompt through the Antigravity Runtime."""
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    runtime = AntigravityRuntime()
    result = await runtime.run_turn(prompt)
    return {"status": "success", "response": result, "conversation_id": runtime.conversation_id}

@app.get("/api/workflows")
async def get_workflows():
    """Returns the AntigravityKit 16 workflows registry."""
    if WORKFLOWS_PATH.exists():
        return json.loads(WORKFLOWS_PATH.read_text(encoding="utf-8"))
    return {"workflows": []}

@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Returns metadata and transcript lines for a specific session."""
    session_dir = settings.SESSION_SAVE_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    meta_path = session_dir / "metadata.json"
    transcript_path = session_dir / "transcript.jsonl"
    
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    transcript = []
    if transcript_path.exists():
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    transcript.append(json.loads(line))
                except Exception:
                    pass
                    
    return {"metadata": metadata, "transcript": transcript}

# -----------------------------------------------------------------------------
# Webhook and Lifecycle Triggers
# -----------------------------------------------------------------------------

@app.post("/triggers/maintenance")
async def trigger_maintenance(background_tasks: BackgroundTasks):
    """Triggered by Cloud Scheduler or manual HTTP POST."""
    logger.info("Received manual/Cloud Scheduler maintenance trigger.")
    background_tasks.add_task(scheduler._hourly_job)
    return {"status": "accepted", "message": "Hourly maintenance job dispatched."}

@app.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event")
):
    """Processes inbound GitHub webhook events."""
    payload: Dict[str, Any] = await request.json()
    logger.info(f"Received GitHub webhook event: {x_github_event}")

    async def process_event():
        runtime = AntigravityRuntime()
        if x_github_event == "issues" and payload.get("action") == "opened":
            issue = payload.get("issue", {})
            prompt = (
                f"[GitHub Webhook Event: Issue #{issue.get('number')} Opened]\n"
                f"Title: {issue.get('title')}\n"
                f"Body: {issue.get('body')}\n"
                "Task: Triage issue, analyze logs if present, and post a diagnostic comment."
            )
            await runtime.run_turn(prompt)

        elif x_github_event == "pull_request" and payload.get("action") == "opened":
            pr = payload.get("pull_request", {})
            prompt = (
                f"[GitHub Webhook Event: PR #{pr.get('number')} Opened]\n"
                f"Title: {pr.get('title')}\n"
                "Task: Run dep-scanner and research subagents to verify code impact."
            )
            await runtime.run_turn(prompt)

    background_tasks.add_task(process_event)
    return {"status": "accepted", "event": x_github_event}

@app.post("/approvals/callback")
async def handle_approval_callback(request: Request):
    """Callback for LinkGravity interactive button approvals (Slack / Telegram / Discord)."""
    payload = await request.json()
    action = payload.get("action")
    tool = payload.get("tool")
    logger.info(f"Received approval callback: action={action}, tool={tool}")
    return {"status": "recorded", "decision": action}

@app.get("/sessions")
async def list_sessions():
    """Returns local active sessions."""
    sessions = []
    if settings.SESSION_SAVE_DIR.exists():
        for item in settings.SESSION_SAVE_DIR.iterdir():
            if item.is_dir():
                sessions.append(item.name)
    return {"active_sessions": sessions}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
