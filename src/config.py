"""Configuration settings for the Antigravity GitHub Ecosystem."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    BASE_DIR: Path = BASE_DIR
    # Environment
    ENV: str = os.getenv("ANTIGRAVITY_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Session & State Persistence
    SESSION_SAVE_DIR: Path = Path(os.getenv("SESSION_SAVE_DIR", str(BASE_DIR / "data" / "sessions"))).resolve()
    TRIGGER_INTERVAL_SECONDS: int = int(os.getenv("TRIGGER_INTERVAL_SECONDS", "3600"))

    # GitHub Credentials & MCP
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPOSITORY: str = os.getenv("GITHUB_REPOSITORY", "")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    # Account whose repositories the daily checkup covers (defaults to the repository owner)
    PORTFOLIO_OWNER: str = os.getenv("PORTFOLIO_OWNER", "")

    # Google Cloud Run
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    CLOUD_RUN_SERVICE_NAME: str = os.getenv("CLOUD_RUN_SERVICE_NAME", "antigravity-agent-daemon")

    # LinkGravity Notifications & Approvals
    LINKGRAVITY_PLATFORM: str = os.getenv("LINKGRAVITY_PLATFORM", "slack").lower()
    LINKGRAVITY_WEBHOOK_URL: str = os.getenv("LINKGRAVITY_WEBHOOK_URL", "")
    LINKGRAVITY_TELEGRAM_BOT_TOKEN: str = os.getenv("LINKGRAVITY_TELEGRAM_BOT_TOKEN", "")
    LINKGRAVITY_TELEGRAM_CHAT_ID: str = os.getenv("LINKGRAVITY_TELEGRAM_CHAT_ID", "")
    LINKGRAVITY_DISCORD_WEBHOOK_URL: str = os.getenv("LINKGRAVITY_DISCORD_WEBHOOK_URL", "")

    # Outbound Generic Webhooks
    OUTBOUND_WEBHOOK_URL: str = os.getenv("OUTBOUND_WEBHOOK_URL", "")
    WEBHOOK_SECRET_KEY: str = os.getenv("WEBHOOK_SECRET_KEY", "")

    # File Paths
    MCP_CONFIG_PATH: Path = BASE_DIR / "mcp_config.json"
    AGENTS_DIR: Path = BASE_DIR / ".agents"

settings = Settings()
