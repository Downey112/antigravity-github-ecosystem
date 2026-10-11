"""PreToolUse Safety Gate Hook Script.

Intercepts destructive commands before they run, gating them for approval.
"""

import json
import sys

DANGEROUS_PATTERNS = [
    "rm -rf", "drop table", "git push --force", "format c:", "mkfs", "dd if="
]

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    tool_call = input_data.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    cmd = args.get("CommandLine", "").lower()

    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd:
            output = {
                "decision": "ask",
                "reason": f"Potentially dangerous operation detected: '{pattern}'. Requires confirmation."
            }
            print(json.dumps(output))
            return

    # Allow safe commands
    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
