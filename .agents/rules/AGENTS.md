# Antigravity Ecosystem Agent Guidelines

## 1. Core Operating Principles
- **Safety First**: Never execute destructive commands (`rm -rf`, `DROP TABLE`, force-pushing to `main`) without going through the PreToolUse safety gate or LinkGravity approval.
- **Progressive Disclosure**: Delegate heavy analysis to specialized subagents (`dep-scanner`, `research`, `browser`) rather than cluttering the primary conversation context.
- **Session Persistence**: Always record state transitions, task progress, and artifacts in `data/sessions/<conversation_id>/`.

## 2. GitHub & Deployment Protocol
- Triage open issues with constructive diagnostic comments before attempting code fixes.
- For dependency vulnerabilities detected by `dep-scanner`, create a descriptive fix branch (e.g. `deps/security-patch-<cve>`) and open a Pull Request via GitHub MCP.
- Before deploying to Cloud Run, verify that container builds and tests pass cleanly, and execute the `browser` subagent to smoke-test endpoints.

## 3. Communication & Human-In-The-Loop
- Send critical operational errors and approval requests via LinkGravity (Slack/Discord/Telegram).
- Include concise reasoning and parameter breakdowns in every approval payload.
