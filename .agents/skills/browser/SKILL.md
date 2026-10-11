---
name: browser
description: >-
  Executes headless browser smoke tests, verifies frontend UI elements, checks HTTP status codes, and captures page screenshots.
---

# Browser Verification Skill (`browser`)

Use this skill when verifying web applications, reviewing UI changes, or validating live Cloud Run deployments.

## Usage

1. **Run Smoke Check**:
   ```bash
   python .agents/skills/browser/scripts/run_browser_check.py https://your-service-url.run.app
   ```

2. **Verify Results**:
   - Check status code (must be 2xx/3xx).
   - Check console errors (must be empty).
   - Review saved screenshot in the session artifacts directory.
