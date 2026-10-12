# Antigravity GitHub Ecosystem

Complete autonomous software engineering and repository operations platform powered by **Google Antigravity**.

```text
┌──────────────────────────────────────────────────────────────────┐
│              ANTIGRAVITY GITHUB ECOSYSTEM (COMPLETE)             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    CORE AGENT RUNTIME                        ││
│  │  • Antigravity SDK (Python)                                  ││
│  │  • Periodic triggers: every(3600)                            ││
│  │  • Lifecycle hooks: pre_turn, on_tool_error                  ││
│  │  • Session persistence: conversation_id + save_dir           ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────────┐│
│  │                    INTEGRATION LAYER                         ││
│  │  • GitHub MCP Server (issues, PRs, releases)                 ││
│  │  • Cloud Run MCP Server (deployment)                         ││
│  │  • AntigravityKit (68 skills, 16 workflows)                  ││
│  └──────────────────────────┼──────────────────────────────────┘│
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────────┐│
│  │                    SUBAGENT LAYER                            ││
│  │  • dep-scanner (dependency analysis)                         ││
│  │  • research (codebase exploration)                           ││
│  │  • browser (UI verification)                                 ││
│  └──────────────────────────┼──────────────────────────────────┘│
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────────┐│
│  │                    DEPLOYMENT LAYER                          ││
│  │  • Cloud Run (serverless, always-on)                         ││
│  │  • GitHub Actions (event-driven, cron)                       ││
│  └──────────────────────────┼──────────────────────────────────┘│
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────────┐│
│  │                    NOTIFICATION LAYER                        ││
│  │  • LinkGravity (Telegram / Slack / Discord)                  ││
│  │  • Webhooks (email, SMS, custom)                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```text
antigravity-github-ecosystem/
├── .agents/                               # Antigravity Workspace Customizations Root
│   ├── hooks.json                         # Native hooks specification: PreToolUse, PostToolUse, PreInvocation
│   ├── rules/
│   │   └── AGENTS.md                      # Workspace & team engineering guidelines
│   ├── skills/
│   │   ├── dep-scanner/                   # Subagent: Dependency security & license audit
│   │   ├── research/                      # Subagent: Codebase AST search & exploration
│   │   ├── browser/                       # Subagent: Headless browser verification
│   │   └── antigravity-kit/               # AntigravityKit workflows registry (16 workflows)
│   └── scripts/
│       ├── safety_check.py                # PreToolUse guardrail script
│       ├── on_tool_error.py               # PostToolUse failure notification script
│       └── pre_turn.py                    # PreInvocation dynamic context injector
├── src/                                   # Python Core Agent Runtime
│   ├── config.py                          # Environment settings
│   ├── runtime.py                         # Antigravity Python SDK runtime loop
│   ├── session.py                         # Persistence engine (conversation_id + save_dir)
│   ├── scheduler.py                       # Periodic trigger engine: every(3600)
│   ├── subagents/
│   │   ├── dep_scanner.py                 # dep-scanner logic
│   │   ├── researcher.py                  # research AST search logic
│   │   └── browser_verifier.py            # browser Playwright logic
│   ├── integrations/
│   │   ├── github_client.py               # GitHub API & MCP wrapper
│   │   ├── cloud_run_client.py            # Cloud Run deployment wrapper
│   │   └── mcp_manager.py                 # Dynamic MCP config generator
│   └── notifications/
│       ├── linkgravity.py                 # Slack / Discord / Telegram bridge & approvals
│       └── webhooks.py                    # Generic outbound webhook dispatcher
├── server.py                              # Cloud Run serverless entrypoint (FastAPI)
├── main.py                                # CLI execution entrypoint
├── mcp_config.json                        # MCP Servers definition
├── Dockerfile                             # Container build for Cloud Run
├── requirements.txt                       # Python dependencies
└── .github/
    └── workflows/
        ├── agent-ci.yml                   # Event-driven: GitHub Issues & PRs
        ├── daily-checkup.yml              # Scheduled daily checkup across all repositories
        └── hourly-cron.yml                # Scheduled hourly trigger: every 3600s
```

---

## 🚀 Quickstart

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Key environment variables:
- `GITHUB_TOKEN`: Personal Access Token with repo scope.
- `GCP_PROJECT_ID`: Google Cloud Project ID for Cloud Run deployments.
- `LINKGRAVITY_WEBHOOK_URL`: Slack/Discord/Telegram webhook for approvals and alerts.

---

## 🛠️ Execution Modes

### Local CLI & Tests
- **Single run (Hourly Audit)**:
  ```bash
  python main.py --cron
  ```
- **Daily Portfolio Checkup** (add `--dry-run` to print the report without publishing it):
  ```bash
  python main.py --checkup
  ```
- **Simulate GitHub Event**:
  ```bash
  python main.py --event issues --action opened
  ```
- **Run AntigravityKit Workflow**:
  ```bash
  python main.py --workflow wf-02-dep-security-patch
  ```
- **Run Continuous Scheduler (`every(3600)`)**:
  ```bash
  python main.py --daemon
  ```

### Serverless Cloud Run Deployment
Build and run locally with Docker:
```bash
docker build -t antigravity-ecosystem .
docker run -p 8080:8080 --env-file .env antigravity-ecosystem
```

Deploy directly to Google Cloud Run:
```bash
gcloud run deploy antigravity-agent-daemon \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### GitHub Actions Automation
- `.github/workflows/agent-ci.yml` triggers automatically whenever issues or PRs are opened.
- `.github/workflows/hourly-cron.yml` executes the hourly maintenance loop at `0 * * * *`.
- `.github/workflows/daily-checkup.yml` checks every repository the account owns at `5 0 * * *` (workflow results, open issues and PRs, live sites, licenses) and keeps the result in a single **Daily Portfolio Checkup** issue.

---

## 🛡️ Security & Lifecycle Hooks
- **`PreToolUse`**: Enforces guardrails via `.agents/scripts/safety_check.py`. Destructive operations require confirmation.
- **`PostToolUse`**: Records telemetry and logs errors to `data/logs/tool_errors.log`.
- **`PreInvocation`**: Injects dynamic context and active subagent manifests before the model runs.
- **LinkGravity HITL**: Sensitive deployments and changes post interactive approval cards to Slack, Discord, or Telegram before executing.
