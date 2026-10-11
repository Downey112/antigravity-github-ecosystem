"""Browser Smoke Check CLI Script."""

import asyncio
import json
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root_dir))

from src.subagents.browser_verifier import BrowserVerificationSubagent

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing URL argument. Usage: run_browser_check.py <url>"}))
        return

    url = sys.argv[1]
    verifier = BrowserVerificationSubagent()
    result = await verifier.verify_endpoint(url)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
