"""Periodic Trigger and Scheduling Engine.

Implements `every(3600)` triggers for continuous repository health checks,
issue triage, and dependency auditing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from src.config import settings
from src.runtime import AntigravityRuntime
from src.notifications.linkgravity import linkgravity

logger = logging.getLogger("PeriodicScheduler")

class PeriodicScheduler:
    """Runs periodic agent routines at fixed intervals."""

    def __init__(self, interval_seconds: int = settings.TRIGGER_INTERVAL_SECONDS):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.runtime = AntigravityRuntime(conversation_id="periodic-maintenance-loop")

    async def _hourly_job(self):
        """Standard hourly maintenance job."""
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info(f"Triggering scheduled hourly maintenance at {timestamp}")

        prompt = (
            f"[SCHEDULED TRIGGER every({self.interval_seconds})]\n"
            "Execute standard maintenance sweep:\n"
            "1. Run dep-scanner for CVEs and outdated dependencies.\n"
            "2. Fetch new unassigned issues and draft triage recommendations.\n"
            "3. If recent commits were deployed to Cloud Run, trigger browser verification."
        )

        try:
            result = await self.runtime.run_turn(prompt)
            await linkgravity.broadcast(
                title=f"Scheduled Maintenance Complete ({self.interval_seconds}s)",
                message=f"Routine maintenance executed successfully.\n\nSummary:\n{result[:300]}...",
                level="SUCCESS",
            )
        except Exception as e:
            logger.error(f"Scheduled maintenance failed: {e}")

    async def start(self):
        """Starts the periodic execution loop."""
        self.is_running = True
        logger.info(f"Scheduler started with interval every({self.interval_seconds}s).")

        while self.is_running:
            try:
                await self._hourly_job()
            except Exception as e:
                logger.error(f"Error in scheduler iteration: {e}")
            
            # Wait for next interval
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        """Halts the scheduler loop."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Scheduler stopped.")

scheduler = PeriodicScheduler()
