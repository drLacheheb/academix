import sys

from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("agent-cleanup")


def main():
    logger.info("Initializing Agent Cleanup...")
    api = make_api_client()

    logger.info("Triggering hard cleanup of expired/404 jobs at /jobs/expired...")
    try:
        resp = api.delete("/jobs/expired")
        deleted_count = resp.json().get("deleted_count", 0)
        logger.info(f"Hard-deleted {deleted_count} expired job records.")
    except Exception as e:
        logger.error(f"Failed to execute expired jobs cleanup: {e}")
        sys.exit(1)


def run():
    main()


if __name__ == "__main__":
    main()
