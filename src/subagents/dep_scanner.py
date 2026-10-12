"""Dependency Scanner Subagent (`dep-scanner`).

Analyzes requirements.txt, package.json, and lockfiles for CVEs,
outdated packages, and license compliance.
"""

import json
import logging
import re
import subprocess
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("dep-scanner")

# Licenses that need a human decision before the project can depend on them
COPYLEFT_PATTERN = re.compile(r"\bA?L?GPL|General Public License", re.IGNORECASE)

class DependencyScannerSubagent:
    """Subagent responsible for dependency auditing and vulnerability triage."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)

    def _requirement_names(self, req_file: Path) -> List[str]:
        """Extracts the declared package names from a requirements file."""
        names: List[str] = []
        for line in req_file.read_text(encoding="utf-8").splitlines():
            match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line.strip())
            if match:
                names.append(match.group(0))
        return names

    def _normalize_pip_audit(self, report: Any) -> Dict[str, Any]:
        """Converts pip-audit JSON output into the scanner's result shape."""
        # Older pip-audit releases emit a bare list instead of {"dependencies": [...]}
        deps = report if isinstance(report, list) else report.get("dependencies", [])
        vulnerabilities = [
            {
                "package": dep.get("name"),
                "version": dep.get("version"),
                "id": vuln.get("id"),
                "fix_versions": vuln.get("fix_versions", []),
            }
            for dep in deps
            for vuln in dep.get("vulns", [])
        ]
        return {
            "status": "completed",
            "scanner": "pip-audit",
            "audited": True,
            "packages_found": len(deps),
            "vulnerabilities": vulnerabilities,
        }

    def scan_python_dependencies(self) -> Dict[str, Any]:
        """Runs pip-audit or static manifest scan on Python requirements."""
        req_file = self.workspace_root / "requirements.txt"
        if not req_file.exists():
            return {"status": "skipped", "message": "No requirements.txt found"}

        # Attempt pip-audit if installed (exits non-zero when it finds vulnerabilities)
        try:
            res = subprocess.run(
                ["pip-audit", "-r", str(req_file), "-f", "json"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                timeout=300,
            )
            if res.stdout.strip():
                return self._normalize_pip_audit(json.loads(res.stdout))
            logger.warning(f"pip-audit produced no report: {res.stderr.strip()[-300:]}")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.info("pip-audit not installed or timed out. Falling back to static parsing.")
        except json.JSONDecodeError:
            logger.warning("pip-audit output was not valid JSON. Falling back to static parsing.")

        # Fallback static parse: counts declared packages, but checks nothing for CVEs
        packages = self._requirement_names(req_file)

        return {
            "status": "completed",
            "scanner": "static-fallback",
            "audited": False,
            "packages_found": len(packages),
            "packages": packages,
            "vulnerabilities": [],
        }

    def _license_of(self, package: str) -> Optional[str]:
        """Reads the license an installed package declares in its metadata."""
        try:
            meta = metadata(package)
        except PackageNotFoundError:
            return None

        license_name = meta.get("License-Expression") or ""
        if not license_name:
            classifiers = [
                c.split("::")[-1].strip()
                for c in meta.get_all("Classifier") or []
                if c.startswith("License ::")
            ]
            license_name = ", ".join(classifiers)
        if not license_name:
            raw = (meta.get("License") or "").strip()
            license_name = raw.splitlines()[0][:60] if raw else ""
        return license_name or None

    def scan_licenses(self) -> Dict[str, Any]:
        """Reports the declared license of each package in requirements.txt."""
        req_file = self.workspace_root / "requirements.txt"
        if not req_file.exists():
            return {"status": "skipped", "message": "No requirements.txt found"}

        packages = []
        for name in self._requirement_names(req_file):
            license_name = self._license_of(name)
            if license_name is None:
                flag = "unknown"
            elif COPYLEFT_PATTERN.search(license_name):
                flag = "copyleft"
            else:
                flag = "ok"
            packages.append({"package": name, "license": license_name, "flag": flag})

        return {"status": "completed", "packages": packages}

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
            "licenses": self.scan_licenses(),
        }

    def summarize(self, audit: Dict[str, Any]) -> List[str]:
        """Renders an audit as markdown bullet lines, stating only what was checked."""
        py = audit.get("python", {})
        if py.get("status") != "completed":
            return [f"- **Python dependencies**: skipped ({py.get('message', 'no result')})"]

        lines = [
            f"- **Scanner**: `{py.get('scanner')}`",
            f"- **Packages Scanned**: `{py.get('packages_found', 0)}`",
        ]

        vulns = py.get("vulnerabilities", [])
        if not py.get("audited"):
            lines.append("- **Vulnerabilities**: not checked (pip-audit did not produce a report)")
        elif not vulns:
            lines.append("- **Vulnerabilities**: none known")
        else:
            lines.append(f"- **Vulnerabilities**: `{len(vulns)}` found")
            for v in vulns[:20]:
                fix = ", ".join(v.get("fix_versions") or []) or "no fix released"
                lines.append(f"  - `{v['package']} {v['version']}`: {v['id']} (fix: {fix})")
            if len(vulns) > 20:
                lines.append(f"  - …and {len(vulns) - 20} more")

        licensed = audit.get("licenses", {}).get("packages", [])
        if licensed:
            review = [p for p in licensed if p["flag"] != "ok"]
            if not review:
                lines.append(f"- **Licenses**: `{len(licensed)}` direct dependencies checked, none copyleft or unknown")
            else:
                lines.append(f"- **Licenses**: `{len(review)}` of `{len(licensed)}` direct dependencies need review")
                for p in review:
                    lines.append(f"  - `{p['package']}`: {p['license'] or 'license not declared or package not installed'}")

        return lines
