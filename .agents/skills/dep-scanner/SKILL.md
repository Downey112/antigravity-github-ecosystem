---
name: dep-scanner
description: >-
  Audits project dependencies for known security vulnerabilities (CVEs), license compliance, and out-of-date versions. Use when checking security or upgrading packages.
---

# Dependency Scanner Skill (`dep-scanner`)

This skill provides step-by-step instructions for inspecting dependencies and proposing non-breaking security upgrades.

## When to Use
- Triggered automatically during hourly maintenance (`every(3600)`).
- When a user asks to verify security vulnerabilities or update `requirements.txt` / `package.json`.

## Procedure

1. **Execute Scanner Script**:
   Run the scanner helper script:
   ```bash
   python .agents/skills/dep-scanner/scripts/scan_dependencies.py
   ```

2. **Analyze Output**:
   - Inspect any reported CVE IDs, CVSS scores, and fixed version recommendations.
   - If vulnerabilities exist:
     - Check release notes for breaking changes.
     - Bump package version in the requirement file.
     - Run regression test suite.

3. **Stage Pull Request**:
   Use GitHub MCP (`create_pull_request`) to submit the fix branch for review.
