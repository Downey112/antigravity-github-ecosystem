"""MCP Server Management and Configuration Loader."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict
from src.config import settings

class MCPManager:
    """Manages Model Context Protocol configurations and validation."""

    def __init__(self, config_path: Path = settings.MCP_CONFIG_PATH):
        self.config_path = Path(config_path)

    def load_resolved_config(self) -> Dict[str, Any]:
        """Loads mcp_config.json and expands all ${ENV_VAR} placeholders."""
        if not self.config_path.exists():
            return {"mcpServers": {}}

        raw_text = self.config_path.read_text(encoding="utf-8")
        
        # Regex to substitute ${VAR} with environment variables
        pattern = re.compile(r"\$\{([A-Za-z0-9_]+)\}")

        def replace_env(match):
            var_name = match.group(1)
            return os.getenv(var_name, "")

        resolved_text = pattern.sub(replace_env, raw_text)
        return json.loads(resolved_text)

    def generate_runtime_config(self, target_path: Path) -> Path:
        """Writes an expanded mcp_config.json to the agent's runtime directory."""
        data = self.load_resolved_config()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return target_path

mcp_manager = MCPManager()
