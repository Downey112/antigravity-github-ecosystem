"""Cloud Run Integration Client for Continuous Serverless Deployment."""

import logging
import subprocess
from typing import Any, Dict, Optional
from src.config import settings

logger = logging.getLogger("CloudRunClient")

class CloudRunClient:
    """Manages deployments and status checks for Google Cloud Run services."""

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.region = settings.GCP_REGION
        self.service_name = settings.CLOUD_RUN_SERVICE_NAME

    def get_service_status(self) -> Dict[str, Any]:
        """Checks the current live URL and revision of the Cloud Run service via gcloud."""
        if not self.project_id:
            return {"status": "unconfigured", "service": self.service_name}

        cmd = [
            "gcloud", "run", "services", "describe", self.service_name,
            f"--project={self.project_id}",
            f"--region={self.region}",
            "--format=json"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(res.stdout)
            return {
                "status": "ready",
                "url": data.get("status", {}).get("url", ""),
                "latestCreatedRevision": data.get("status", {}).get("latestCreatedRevisionName", ""),
                "latestReadyRevision": data.get("status", {}).get("latestReadyRevisionName", ""),
            }
        except Exception as e:
            logger.warning(f"Failed to query Cloud Run status: {e}")
            return {"status": "error", "message": str(e)}

    def deploy_new_image(self, image_uri: str) -> Dict[str, Any]:
        """Triggers deployment of a container image to Cloud Run."""
        cmd = [
            "gcloud", "run", "deploy", self.service_name,
            f"--image={image_uri}",
            f"--project={self.project_id}",
            f"--region={self.region}",
            "--platform=managed",
            "--allow-unauthenticated",
            "--format=json"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            return json.loads(res.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Cloud Run deployment failed: {e.stderr}")
            return {"error": e.stderr}

cloud_run_client = CloudRunClient()
