"""PostToolUse Telemetry and Error Hook Script."""

import json
import os
import sys
from datetime import datetime, timezone

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return

    error = input_data.get("error")
    if error:
        # Write error telemetry log
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "tool_errors.log")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] Step {input_data.get('stepIdx')}: {error}\n")

    print("{}")

if __name__ == "__main__":
    main()
