"""PreInvocation Dynamic Context Injector."""

import json
import os
import sys

def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"injectSteps": []}))
        return

    # Dynamic context injection: remind agent of active rules and environment status
    msg = (
        "[Antigravity Runtime Notice] Pre-turn hooks active. "
        "Subagents: dep-scanner, research, browser. "
        "Sensitive deployments to Cloud Run require approval via LinkGravity."
    )

    output = {
        "injectSteps": [
            {
                "ephemeralMessage": msg
            }
        ]
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
