---
name: antigravity-kit
description: >-
  Provides 68 specialized skills and 16 automated engineering workflows for repository maintenance, vibe coding, CI/CD triage, and continuous Cloud Run deployments.
---

# AntigravityKit (AG Kit)

AntigravityKit packages modular engineering procedures and workflows into an orchestrated library.

## Workflow Reference
The full registry of 16 workflows is located in [workflows.json](./workflows.json).

### Key Workflows:
1. `wf-01-issue-triage`: Classifies inbound issues and drafts automated diagnostic repros.
2. `wf-02-dep-security-patch`: Runs `dep-scanner`, verifies CVE fixes, and opens remediation PRs.
3. `wf-03-cloud-run-deploy`: Gated Cloud Run rollouts with LinkGravity approvals and browser smoke verification.
4. `wf-06-chatops-approval`: Formats interactive Slack/Discord/Telegram approval cards.

## Executing a Workflow
To execute a workflow, invoke the Antigravity Runtime with the workflow ID and payload parameters:
```bash
python main.py --workflow wf-02-dep-security-patch
```
