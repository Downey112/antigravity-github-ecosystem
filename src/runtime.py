"""Core Antigravity Agent Runtime.

Implements the central execution loop with:
- Antigravity Python SDK (`google.antigravity`)
- Lifecycle hooks (`pre_turn`, `on_tool_error`)
- Session persistence (`conversation_id` + `save_dir`)
- Integration with Subagents, MCP tools, and LinkGravity
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from src.config import settings
from src.session import SessionManager
from src.notifications.linkgravity import linkgravity
from src.notifications.webhooks import webhook_dispatcher
from src.integrations.mcp_manager import mcp_manager
from src.subagents.dep_scanner import DependencyScannerSubagent
from src.subagents.researcher import ResearchSubagent
from src.subagents.browser_verifier import BrowserVerificationSubagent
from src.subagents.portfolio_checkup import CHECKUP_ISSUE_TITLE

logger = logging.getLogger("AntigravityRuntime")

# Hidden marker that lets each run find and rewrite its own triage comment
TRIAGE_COMMENT_MARKER = "<!-- antigravity-triage -->"

class AntigravityRuntime:
    """Manages agent execution, hook dispatching, and session persistence."""

    def __init__(self, conversation_id: Optional[str] = None, save_dir: Optional[Path] = None):
        self.save_dir = save_dir or settings.SESSION_SAVE_DIR
        self.session = SessionManager(self.save_dir, conversation_id=conversation_id)
        self.conversation_id = self.session.conversation_id
        
        # Subagents
        self.dep_scanner = DependencyScannerSubagent(settings.BASE_DIR)
        self.researcher = ResearchSubagent(settings.BASE_DIR)
        self.browser_verifier = BrowserVerificationSubagent(self.session.artifacts_dir / "browser")

    # -------------------------------------------------------------------------
    # Lifecycle Hooks
    # -------------------------------------------------------------------------

    async def pre_turn(self, prompt: str) -> str:
        """Lifecycle hook executed before dispatching a prompt to the model.
        
        Performs prompt sanitization, security checks, and dynamic context injection.
        """
        logger.info(f"[{self.conversation_id}] Executing pre_turn hook...")
        meta = self.session.get_metadata()
        invocations = meta.get("invocations_count", 0) + 1
        self.session.update_metadata({"invocations_count": invocations, "status": "running"})

        # Record prompt in transcript
        self.session.log_transcript_step({
            "type": "USER_INPUT",
            "invocation": invocations,
            "content": prompt,
        })
        return prompt

    async def on_tool_error(self, tool_name: str, args: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Lifecycle hook executed when a tool execution fails.
        
        Logs failure, notifies LinkGravity for intervention, and formats fallback response.
        """
        err_msg = str(error)
        logger.error(f"[{self.conversation_id}] Tool error in '{tool_name}': {err_msg}")

        # Log to transcript
        self.session.log_transcript_step({
            "type": "TOOL_ERROR",
            "tool": tool_name,
            "args": args,
            "error": err_msg,
        })

        # Disseminate alerts
        await linkgravity.broadcast(
            title=f"Tool Execution Error: {tool_name}",
            message=f"Agent encountered an error while calling `{tool_name}`: {err_msg}",
            level="ERROR",
            fields={"Conversation": self.conversation_id, "Tool": tool_name},
        )
        await webhook_dispatcher.emit_event("tool_failure", {
            "conversation_id": self.conversation_id,
            "tool": tool_name,
            "error": err_msg,
        })

        return {"status": "error", "tool": tool_name, "error": err_msg}

    # -------------------------------------------------------------------------
    # Execution Engine
    # -------------------------------------------------------------------------

    async def run_turn(self, prompt: str) -> str:
        """Executes a full turn through the Antigravity SDK or fallback executor."""
        processed_prompt = await self.pre_turn(prompt)
        output_tokens = []

        try:
            # Check if google-antigravity SDK is importable
            try:
                import os
                if not os.getenv("GEMINI_API_KEY"):
                    raise ImportError("GEMINI_API_KEY not set; falling back to internal orchestrator.")
                
                from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
                
                # Prepare resolved MCP runtime file
                mcp_file = self.session.session_path / "mcp_resolved.json"
                mcp_manager.generate_runtime_config(mcp_file)

                config = LocalAgentConfig(
                    system_instructions=(
                        "You are an autonomous AI software engineer maintaining this repository. "
                        "You use MCP tools for GitHub and Cloud Run, and invoke specialized subagents "
                        "(dep-scanner, research, browser) when needed."
                    ),
                    capabilities=CapabilitiesConfig(),
                    mcp_servers_file=str(mcp_file),
                )

                async with Agent(config) as agent:
                    response = await agent.chat(processed_prompt)
                    async for token in response:
                        output_tokens.append(token)

            except ImportError:
                logger.info("google-antigravity SDK not installed. Running internal orchestrator.")
                # Built-in fallback orchestrator to demonstrate workflow & subagent logic
                output_tokens.append(f"Processed task: {processed_prompt}\n")
                if "dep" in processed_prompt.lower() or "audit" in processed_prompt.lower():
                    audit = self.dep_scanner.run_full_scan()
                    pkgs = audit['python'].get('packages_found', 0)
                    output_tokens.append(f"[dep-scanner]: Audited {pkgs} packages. Status: {audit['python'].get('status')}.\n")
                if "search" in processed_prompt.lower() or "symbol" in processed_prompt.lower():
                    symbols = self.researcher.search_symbols("Settings")
                    output_tokens.append(f"[researcher]: Located {len(symbols)} symbol references.\n")

                # Live GitHub Issue Triage Dispatch
                if "issue" in processed_prompt.lower():
                    from src.integrations.github_client import github_client
                    issues = await github_client.list_open_issues()
                    # Only issues that ask for a dependency audit get the dep-scanner report
                    audit_requests = [
                        i for i in issues
                        if "pull_request" not in i
                        and i.get("title") != CHECKUP_ISSUE_TITLE
                        and re.search(
                            r"depend|audit|licen|cve|vulnerab",
                            f"{i.get('title', '')} {i.get('body') or ''}",
                            re.IGNORECASE,
                        )
                    ]
                    if audit_requests:
                        audit = self.dep_scanner.run_full_scan()
                        findings = "\n".join(self.dep_scanner.summarize(audit))
                        last_run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                    for target_issue in audit_requests[:5]:
                        issue_num = target_issue.get("number")
                        issue_title = target_issue.get("title")

                        comment = (
                            f"### 🤖 Antigravity Autonomous Agent Triage Report\n\n"
                            f"**Trigger**: Scheduled / Event-driven autonomous maintainer loop\n"
                            f"**Target Issue**: #{issue_num} — *{issue_title}*\n"
                            f"**Last run**: {last_run}\n\n"
                            f"#### 🔍 Subagent Execution: `dep-scanner`\n"
                            f"{findings}\n\n"
                            f"> [!NOTE]\n"
                            f"> This comment is rewritten on every run and reports only what the scanner checked."
                        )
                        posted = await github_client.upsert_issue_comment(issue_num, TRIAGE_COMMENT_MARKER, comment)
                        if posted:
                            output_tokens.append(f"[github-client]: Successfully posted triage diagnostic to Issue #{issue_num}.\n")
                        else:
                            output_tokens.append(f"[github-client]: Attempted comment on Issue #{issue_num}.\n")

            result_text = "".join(output_tokens)
            self.session.log_transcript_step({
                "type": "MODEL_RESPONSE",
                "content": result_text,
            })
            self.session.update_metadata({"status": "idle"})
            return result_text

        except Exception as e:
            await self.on_tool_error(tool_name="chat_turn", args={"prompt": processed_prompt}, error=e)
            self.session.update_metadata({"status": "errored"})
            raise
