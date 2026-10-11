"""CLI and Local Execution Entrypoint for Antigravity GitHub Ecosystem."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.config import settings
from src.runtime import AntigravityRuntime
from src.scheduler import scheduler

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
    parser.add_argument("--chat", type=str, help="Execute an arbitrary agent chat prompt")
    parser.add_argument("--event", type=str, help="Simulate or handle a GitHub event (e.g. issues)")
    parser.add_argument("--action", type=str, default="opened", help="GitHub event action")
    parser.add_argument("--workflow", type=str, help="Execute an AntigravityKit workflow by ID")

    args = parser.parse_args()

    if args.cron:
        asyncio.run(run_cron_cycle())
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
