"""Cloud Run Serverless Agent Entrypoint.

Exposes HTTP endpoints for:
- Cloud Run health & liveness probes
- GitHub webhook events (issues, PRs, releases)
- Cloud Scheduler / cron maintenance triggers
- LinkGravity interactive approval callbacks
"""

import asyncio
import logging
from typing import Any, Dict
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.runtime import AntigravityRuntime
from src.scheduler import scheduler
from src.notifications.linkgravity import linkgravity

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("CloudRunServer")

app = FastAPI(
    title="Antigravity GitHub Ecosystem Daemon",
    version="1.0.0",
    description="Autonomous Cloud Run agent daemon with GitHub MCP and LinkGravity integrations."
)

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Antigravity Cloud Run Daemon...")
    # Optional: Start scheduler task in background if ALWAYS_ON is desired
    if settings.ENV == "production":
        asyncio.create_task(scheduler.start())

@app.get("/health")
async def health_check():
    """Liveness probe for Cloud Run."""
    return {
        "status": "healthy",
        "service": settings.CLOUD_RUN_SERVICE_NAME,
        "region": settings.GCP_REGION,
        "environment": settings.ENV,
    }

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
