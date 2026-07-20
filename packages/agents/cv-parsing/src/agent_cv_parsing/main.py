import os
import gc
import socket
from dotenv import load_dotenv

from core.infrastructure.logging.logger import get_logger
from core.utils.agent import run_agent_loop
from core.utils.api import make_api_client
from core.infrastructure.services.pdf_parser import parse_pdf_to_markdown
from core.infrastructure.services.storage import get_storage_service_from_env

load_dotenv()

# Setup logging
logger = get_logger("cv-parsing-worker")

AGENT_NAME = (
    f"{os.environ.get('AGENT_NAME', 'cv-parsing-worker')}-{socket.gethostname()}"
)


def process_ingestion_task(client) -> bool:
    # Query API for pending CV ingestion task
    try:
        resp = client.post("/profiles/claim-ingest", json={"agent_name": AGENT_NAME})
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to poll/claim CV ingestion task from API: {e}")
        return False

    payload = resp.json()
    profile_data = payload.get("profile")
    if not profile_data:
        return False  # No task pending

    profile_id = profile_data["id"]
    file_path = profile_data["cv_file_path"]
    logger.info(
        f"Successfully claimed CV Ingestion Task for Profile ID: {profile_id} (File: {file_path})"
    )

    local_file_path = None
    is_temp_file = False

    try:
        storage_service = get_storage_service_from_env()
        local_file_path, is_temp_file = storage_service.get_local_path(file_path)
        if not local_file_path or not os.path.exists(local_file_path):
            raise FileNotFoundError(
                f"Resolved file path {local_file_path} not found on disk."
            )
    except Exception as e:
        error_msg = f"Failed to retrieve CV file path for {file_path}: {e}"
        logger.error(error_msg, exc_info=True)
        try:
            client.put(
                f"/profiles/fail-ingest/{profile_id}", json={"error_message": error_msg}
            )
        except Exception as api_err:
            logger.error(f"Failed to submit failure status to API: {api_err}")
        return True

    try:
        # Step 1: Parse PDF to markdown text using Docling layout analyzer
        logger.info(
            f"[{profile_id}] Extracting layout and parsing PDF to markdown using Docling..."
        )
        raw_markdown = parse_pdf_to_markdown(local_file_path)

        # Step 2: Upload raw text to API gateway, transitioning state to PENDING_DETECTION
        logger.info(f"[{profile_id}] Uploading raw parsed text to API gateway...")
        client.put(
            f"/profiles/submit-raw-text/{profile_id}",
            json={
                "raw_text": raw_markdown,
                "name": profile_data.get("name"),
                "email": profile_data.get("email"),
            },
        )
        logger.info(f"[{profile_id}] Raw text successfully submitted to pipeline!")

    except Exception as e:
        logger.error(
            f"Failed to process CV Ingestion Task for Profile ID {profile_id}: {e}",
            exc_info=True,
        )
        try:
            client.put(
                f"/profiles/fail-ingest/{profile_id}", json={"error_message": str(e)}
            )
        except Exception as api_err:
            logger.error(f"Failed to notify API about parsing failure: {api_err}")
    finally:
        if is_temp_file and local_file_path:
            try:
                storage_service.clean_up(local_file_path)
            except Exception as cleanup_err:
                logger.warning(
                    f"[{profile_id}] Failed to clean up temp file {local_file_path}: {cleanup_err}"
                )
        # Force garbage collection to free ONNX models and layouter caches immediately
        gc.collect()

    return True


def main():
    logger.info(
        f"Starting CV Ingestion and Parsing Worker (agent_name: {AGENT_NAME})..."
    )
    api_client = make_api_client()
    poll_interval = int(os.environ.get("AGENT_POLL_INTERVAL", "10"))

    def cycle() -> bool:
        return process_ingestion_task(api_client)

    run_agent_loop(
        cycle,
        default_interval=poll_interval,
    )


if __name__ == "__main__":
    main()
