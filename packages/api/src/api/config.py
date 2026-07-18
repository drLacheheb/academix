import os
from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///jobs.db")


def get_api_secret() -> str:
    secret = os.environ.get("API_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "API_SECRET_KEY environment variable is required. "
            "Set it before starting the API server."
        )
    return secret


def get_match_threshold() -> float:
    try:
        return float(os.environ.get("MATCH_THRESHOLD", "0.7"))
    except ValueError:
        return 0.7
