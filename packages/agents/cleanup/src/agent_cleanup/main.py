import os
import sys

from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.api_client import APIClient
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("agent-cleanup")


def main():
    logger.info("Initializing Agent Cleanup...")
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_secret = os.environ.get("API_SECRET_KEY", "dev_secret_key")

    api = APIClient(base_url=api_url, secret_key=api_secret)

    logger.info(f"Triggering hard cleanup of expired/404 jobs at {api_url}/jobs/expired...")
    try:
        resp = api.delete("/jobs/expired")
        deleted_count = resp.get("deleted_count", 0)
        logger.success(f"Hard-deleted {deleted_count} expired job records.")
    except Exception as e:
        logger.error(f"Failed to execute expired jobs cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
