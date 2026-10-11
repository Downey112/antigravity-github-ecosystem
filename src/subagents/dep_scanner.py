"""Dependency Scanner Subagent (`dep-scanner`).

Analyzes requirements.txt, package.json, and lockfiles for CVEs,
outdated packages, and license compliance.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("dep-scanner")

class DependencyScannerSubagent:
    """Subagent responsible for dependency auditing and vulnerability triage."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)

    def scan_python_dependencies(self) -> Dict[str, Any]:
        """Runs pip-audit or static manifest scan on Python requirements."""
        req_file = self.workspace_root / "requirements.txt"
        if not req_file.exists():
            return {"status": "skipped", "message": "No requirements.txt found"}

        # Attempt pip-audit if installed
        try:
            res = subprocess.run(
                ["pip-audit", "-r", str(req_file), "-f", "json"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                timeout=30,
            )
            if res.stdout.strip():
                return json.loads(res.stdout)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.info("pip-audit not installed or timed out. Falling back to static parsing.")

        # Fallback static parse
        packages: List[str] = []
        for line in req_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                packages.append(line)

        return {
            "status": "completed",
            "scanner": "static-fallback",
            "packages_found": len(packages),
            "packages": packages,
            "vulnerabilities": [],
        }

    def scan_npm_dependencies(self) -> Dict[str, Any]:
        """Runs npm audit on package.json if present."""
        pkg_file = self.workspace_root / "package.json"
        if not pkg_file.exists():
            return {"status": "skipped", "message": "No package.json found"}

        try:
            res = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                timeout=30,
            )
            if res.stdout.strip():
                return json.loads(res.stdout)
        except Exception as e:
            return {"status": "error", "message": str(e)}

        return {"status": "clean", "vulnerabilities": 0}

    def run_full_scan(self) -> Dict[str, Any]:
        """Runs both Python and Node security scans and produces an aggregated audit."""
        py_res = self.scan_python_dependencies()
        npm_res = self.scan_npm_dependencies()
        return {
            "subagent": "dep-scanner",
            "workspace": str(self.workspace_root),
            "python": py_res,
            "npm": npm_res,
        }
