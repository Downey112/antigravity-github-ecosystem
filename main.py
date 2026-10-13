"""CLI and Local Execution Entrypoint for Antigravity GitHub Ecosystem."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.config import settings
from src.integrations.github_client import github_client
from src.notifications.linkgravity import linkgravity
from src.runtime import AntigravityRuntime
from src.scheduler import scheduler
from src.subagents.portfolio_checkup import CHECKUP_ISSUE_TITLE, PortfolioCheckupSubagent

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AntigravityCLI")

async def run_single_prompt(prompt: str):
    runtime = AntigravityRuntime()
    print(f"\n[Antigravity Session: {runtime.conversation_id}]")
    print(f"Executing: {prompt}\n" + "-" * 50)
    result = await runtime.run_turn(prompt)
    print("\n" + "-" * 50 + "\nResult:\n" + result)

async def run_cron_cycle():
    logger.info("Executing scheduled maintenance cycle...")
    await scheduler._hourly_job()

async def run_checkup(dry_run: bool = False):
    owner = settings.PORTFOLIO_OWNER or settings.GITHUB_REPOSITORY.split("/")[0]
    if not owner:
        sys.exit("Set PORTFOLIO_OWNER or GITHUB_REPOSITORY to choose whose repositories to check.")

    checkup = PortfolioCheckupSubagent(owner)
    result = await checkup.run()
    report = checkup.render_report(result)
    print(report)
    if dry_run:
        return

    issue_number = await github_client.upsert_issue(CHECKUP_ISSUE_TITLE, report)
    if issue_number is None:
        sys.exit("Checkup ran, but the report issue could not be written.")
    logger.info(f"Checkup report written to issue #{issue_number}.")

    if result["problem_count"]:
        problems = checkup.render_problems(result)
        # A new comment is what notifies the owner; editing the issue body does not
        await github_client.create_issue_comment(
            issue_number, f"**{result['generated_at']}**: needs attention\n\n{problems}"
        )
        await linkgravity.broadcast(
            title=f"Daily Portfolio Checkup: {result['problem_count']} need attention",
            message=problems,
            level="WARNING",
        )

async def run_event(event: str, action: str):
    runtime = AntigravityRuntime()
    prompt = f"[GitHub Event: {event} (action: {action})]\nAnalyze and execute required triage or test steps."
    await runtime.run_turn(prompt)

async def run_workflow(workflow_id: str):
    runtime = AntigravityRuntime()
    prompt = f"[AntigravityKit Workflow Execution]\nRun workflow '{workflow_id}' according to .agents/skills/antigravity-kit/workflows.json."
    await runtime.run_turn(prompt)

def main():
    parser = argparse.ArgumentParser(description="Antigravity GitHub Ecosystem CLI")
    parser.add_argument("--cron", action="store_true", help="Run the single hourly maintenance cycle")
    parser.add_argument("--daemon", action="store_true", help="Start the continuous every(3600) scheduler daemon")
    parser.add_argument("--checkup", action="store_true", help="Run the daily checkup across all of the owner's repositories")
    parser.add_argument("--dry-run", action="store_true", help="With --checkup, print the report without publishing it")
    parser.add_argument("--chat", type=str, help="Execute an arbitrary agent chat prompt")
    parser.add_argument("--event", type=str, help="Simulate or handle a GitHub event (e.g. issues)")
    parser.add_argument("--action", type=str, default="opened", help="GitHub event action")
    parser.add_argument("--workflow", type=str, help="Execute an AntigravityKit workflow by ID")

    args = parser.parse_args()

    if args.cron:
        asyncio.run(run_cron_cycle())
    elif args.checkup:
        asyncio.run(run_checkup(dry_run=args.dry_run))
    elif args.daemon:
        asyncio.run(scheduler.start())
    elif args.workflow:
        asyncio.run(run_workflow(args.workflow))
    elif args.event:
        asyncio.run(run_event(args.event, args.action))
    elif args.chat:
        asyncio.run(run_single_prompt(args.chat))
    else:
        # Default test run
        prompt = "Run standard hourly audit and check project dependencies with dep-scanner."
        asyncio.run(run_single_prompt(prompt))

if __name__ == "__main__":
    main()
