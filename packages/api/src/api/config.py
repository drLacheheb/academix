import os

from core.infrastructure.logging.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("api-config")

INSECURE_DEFAULT_SECRETS = {"dev_secret_key", "your-api-secret-key-here", "changeme", "secret"}


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///academix.db")


def get_api_secret() -> str:
    secret = os.environ.get("API_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "API_SECRET_KEY environment variable is required. "
            "Set it before starting the API server."
        )
    if secret.strip() in INSECURE_DEFAULT_SECRETS:
        logger.warning(
            "API_SECRET_KEY is using a default insecure placeholder value. "
            "Ensure a strong secret is configured for production deployments."
        )
    return secret


def get_match_threshold() -> float:
    try:
        return float(os.environ.get("MATCH_THRESHOLD", "0.7"))
    except ValueError:
        return 0.7
