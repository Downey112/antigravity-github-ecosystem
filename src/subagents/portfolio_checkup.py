"""Portfolio Checkup Subagent (`portfolio-checkup`).

Runs a daily health check across every repository the account owns:
workflow status, open issues and pull requests, missing licenses,
and reachability of each repository's live site.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from src.integrations.github_client import github_client

logger = logging.getLogger("portfolio-checkup")

CHECKUP_ISSUE_TITLE = "Daily Portfolio Checkup"
CHECKUP_MARKER = "<!-- antigravity-portfolio-checkup -->"

FAILED_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}
# GitHub reports NOASSERTION for a license file it cannot match to a known license
LICENSE_LABELS = {None: "⚠️ none", "NOASSERTION": "custom"}

class PortfolioCheckupSubagent:
    """Subagent responsible for the cross-repository daily checkup."""

    def __init__(self, owner: str):
        self.owner = owner

    async def _check_workflows(self, full_name: str) -> List[Dict[str, Any]]:
        """Returns the latest completed run of each workflow in a repository."""
        data = await github_client.get_json(
            f"/repos/{full_name}/actions/runs", params={"per_page": 50, "status": "completed"}
        )
        latest: Dict[int, Dict[str, Any]] = {}
        # Runs arrive newest first, so the first one seen per workflow is the latest
        for run in (data or {}).get("workflow_runs", []):
            latest.setdefault(run["workflow_id"], run)
        return [
            {"name": r["name"], "conclusion": r["conclusion"], "url": r["html_url"]}
            for r in latest.values()
        ]

    async def _check_site(self, url: str) -> Dict[str, Any]:
        """Requests a repository's homepage and reports whether it answered."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(url, headers={"User-Agent": "Antigravity-Agent/1.0"})
            # Streamlit answers scripted clients with a login redirect, awake or asleep,
            # so a redirect only shows the host is reachable
            return {"url": url, "status": res.status_code, "ok": res.status_code < 400}
        except Exception as e:
            return {"url": url, "status": type(e).__name__, "ok": False}

    async def check_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Collects the health signals for one repository."""
        full_name = repo["full_name"]
        result: Dict[str, Any] = {
            "name": repo["name"],
            "url": repo["html_url"],
            "pushed_at": (repo.get("pushed_at") or "")[:10],
            "license": (repo.get("license") or {}).get("spdx_id"),
            "workflows": await self._check_workflows(full_name),
            "issues": [],
            "pulls": [],
            "site": None,
        }

        if repo.get("open_issues_count"):
            items = await github_client.get_json(
                f"/repos/{full_name}/issues", params={"state": "open", "per_page": 100}
            )
            for item in items or []:
                if item.get("title") == CHECKUP_ISSUE_TITLE:
                    continue
                kind = "pulls" if "pull_request" in item else "issues"
                result[kind].append({"number": item["number"], "title": item["title"], "url": item["html_url"]})

        if repo.get("homepage"):
            result["site"] = await self._check_site(repo["homepage"])

        problems = [
            f"workflow [{w['name']}]({w['url']}) ended in `{w['conclusion']}`"
            for w in result["workflows"]
            if w["conclusion"] in FAILED_CONCLUSIONS
        ]
        if result["site"] and not result["site"]["ok"]:
            problems.append(f"live site {result['site']['url']} returned `{result['site']['status']}`")
        result["problems"] = problems
        return result

    async def run(self) -> Dict[str, Any]:
        """Checks every repository the owner maintains (forks and archives excluded)."""
        repos = await github_client.get_json(
            f"/users/{self.owner}/repos", params={"type": "owner", "per_page": 100, "sort": "pushed"}
        )
        if repos is None:
            raise RuntimeError(f"Could not list repositories for '{self.owner}'")

        active = [r for r in repos if not r.get("fork") and not r.get("archived")]
        checked = await asyncio.gather(*(self.check_repo(r) for r in active))
        return {
            "owner": self.owner,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "repos": list(checked),
            "problem_count": sum(len(r["problems"]) for r in checked),
        }

    def render_problems(self, result: Dict[str, Any]) -> str:
        """Renders the items needing attention as a markdown list."""
        return "\n".join(
            f"- **[{r['name']}]({r['url']})**: {problem}"
            for r in result["repos"]
            for problem in r["problems"]
        )

    def render_report(self, result: Dict[str, Any]) -> str:
        """Renders the full checkup as the markdown body of the checkup issue."""
        repos = result["repos"]
        count = result["problem_count"]
        headline = f"**{count} need attention**" if count else "nothing needs attention"
        lines = [
            CHECKUP_MARKER,
            f"Last run: {result['generated_at']} · {len(repos)} repositories · {headline}",
            "",
        ]

        if count:
            lines += ["### Needs attention", self.render_problems(result), ""]

        open_items = [
            f"- {r['name']} [#{i['number']}]({i['url']}): {i['title']}"
            for r in repos
            for i in r["pulls"] + r["issues"]
        ]
        if open_items:
            lines += ["### Open issues and pull requests", *open_items, ""]

        lines += [
            "### All repositories",
            "| Repository | Workflows | Issues | PRs | Live site | License | Last push |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in repos:
            if not r["workflows"]:
                workflows = "none"
            else:
                failed = sum(w["conclusion"] in FAILED_CONCLUSIONS for w in r["workflows"])
                workflows = f"❌ {failed} failing" if failed else f"✅ {len(r['workflows'])} passing"
            if r["site"] is None:
                site = "none"
            else:
                site = f"{'✅' if r['site']['ok'] else '❌'} [{r['site']['status']}]({r['site']['url']})"
            lines.append(
                f"| [{r['name']}]({r['url']}) | {workflows} | {len(r['issues'])} | {len(r['pulls'])} "
                f"| {site} | {LICENSE_LABELS.get(r["license"], r["license"])} | {r['pushed_at']} |"
            )

        lines += [
            "",
            "> Written by the `portfolio-checkup` subagent. This issue is rewritten on every run; "
            "a comment is added only when something needs attention.",
        ]
        return "\n".join(lines)
