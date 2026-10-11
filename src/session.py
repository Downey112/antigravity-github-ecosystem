"""Session Persistence Module for Antigravity Agents.

Handles conversation_id lifecycle, save_dir management, checkpointing,
and transcript serialization across recurrent or event-driven triggers.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

class SessionManager:
    """Manages persistent state and storage for an Antigravity agent session."""

    def __init__(self, save_dir: Path, conversation_id: Optional[str] = None):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.session_path = self.save_dir / self.conversation_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.session_path / "metadata.json"
        self.transcript_file = self.session_path / "transcript.jsonl"
        self.artifacts_dir = self.session_path / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._init_session()

    def _init_session(self):
        """Initializes or loads session metadata."""
        if not self.metadata_file.exists():
            now = datetime.now(timezone.utc).isoformat()
            initial_metadata = {
                "conversation_id": self.conversation_id,
                "created_at": now,
                "updated_at": now,
                "invocations_count": 0,
                "status": "initialized",
                "checkpoints": [],
                "tags": [],
            }
            self.metadata_file.write_text(json.dumps(initial_metadata, indent=2), encoding="utf-8")

    def get_metadata(self) -> Dict[str, Any]:
        """Reads current session metadata."""
        if self.metadata_file.exists():
            return json.loads(self.metadata_file.read_text(encoding="utf-8"))
        return {}

    def update_metadata(self, updates: Dict[str, Any]):
        """Updates and persists session metadata."""
        current = self.get_metadata()
        current.update(updates)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.metadata_file.write_text(json.dumps(current, indent=2), encoding="utf-8")

    def log_transcript_step(self, step_data: Dict[str, Any]):
        """Appends a step or turn to transcript.jsonl."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **step_data,
        }
        with self.transcript_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def record_checkpoint(self, checkpoint_name: str, payload: Dict[str, Any]):
        """Records an execution checkpoint to allow rollbacks or resumed tasks."""
        meta = self.get_metadata()
        checkpoints = meta.get("checkpoints", [])
        checkpoint_entry = {
            "name": checkpoint_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        checkpoints.append(checkpoint_entry)
        meta["checkpoints"] = checkpoints
        self.update_metadata(meta)

    def save_artifact(self, filename: str, content: str) -> Path:
        """Saves a generated artifact (plan, patch, report) to the session artifacts dir."""
        dest = self.artifacts_dir / filename
        dest.write_text(content, encoding="utf-8")
        return dest
