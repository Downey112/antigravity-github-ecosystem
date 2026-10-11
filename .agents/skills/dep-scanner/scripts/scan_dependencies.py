"""Dependency Scanner CLI Script."""

import json
import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root_dir))

from src.subagents.dep_scanner import DependencyScannerSubagent

def main():
    scanner = DependencyScannerSubagent(root_dir)
    report = scanner.run_full_scan()
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
