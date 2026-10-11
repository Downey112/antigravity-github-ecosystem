"""Research Subagent (`research`).

Performs read-only codebase exploration, AST pattern searches,
file tree indexing, and documentation synthesis.
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("research")

class ResearchSubagent:
    """Subagent specialized in deep codebase exploration and semantic indexing."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def search_symbols(self, symbol_name: str, extensions: List[str] = [".py", ".ts", ".js"]) -> List[Dict[str, Any]]:
        """Scans source files to locate class or function definitions matching symbol_name."""
        results: List[Dict[str, Any]] = []

        for ext in extensions:
            for file_path in self.root_dir.rglob(f"*{ext}"):
                if any(ignored in file_path.parts for ignored in [".git", "node_modules", ".venv", "__pycache__"]):
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if ext == ".py":
                        tree = ast.parse(content, filename=str(file_path))
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                if symbol_name.lower() in node.name.lower():
                                    results.append({
                                        "file": str(file_path.relative_to(self.root_dir)),
                                        "symbol": node.name,
                                        "type": type(node).__name__,
                                        "line": node.lineno,
                                    })
                except Exception:
                    continue

        return results

    def inspect_file_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """Produces a structured map of the repository's modules and files."""
        def build_tree(current_dir: Path, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return {}
            tree = {}
            try:
                for item in sorted(current_dir.iterdir()):
                    if item.name.startswith(".") or item.name in ["node_modules", "__pycache__", "venv"]:
                        continue
                    if item.is_dir():
                        tree[item.name + "/"] = build_tree(item, depth + 1)
                    else:
                        tree[item.name] = f"{item.stat().st_size} bytes"
            except PermissionError:
                pass
            return tree

        return build_tree(self.root_dir, 1)
