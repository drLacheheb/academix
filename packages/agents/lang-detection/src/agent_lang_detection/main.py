import argparse
import os
import socket
from dotenv import load_dotenv

from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from agent_lang_detection.detector import LanguageDetector

load_dotenv()


def run():
    parser = argparse.ArgumentParser(description="Job Language Detection Agent")
    parser.add_argument(
        "--name",
        type=str,
        default=f"{os.environ.get('AGENT_NAME', 'lang-detect-worker')}-{socket.gethostname()}",
        help="Custom agent identifier for locking",
    )
    args = parser.parse_args()

    logger = get_logger(args.name)

    logger.info(f"Starting Language Detection Agent (name: {args.name})")

    detector = LanguageDetector()
    api = make_api_client(timeout=60.0)

    from core.utils.agent import run_agent_loop

    def cycle() -> bool:
        nonlocal detector, api, logger
        # 1. Try to claim candidate profile task
        try:
            profile_resp = api.post("/profiles/claim-detect", json={"agent_name": args.name})
            profile_resp.raise_for_status()
            profile_data = profile_resp.json().get("profile")
            if profile_data:
                profile_id = profile_data["id"]
                raw_text = profile_data.get("raw_text") or ""
                logger.info(f"Successfully claimed candidate profile for detection: ID {profile_id}")
                
                lang = detector.detect_lang(raw_text)
                logger.info(f"Detected language for profile ID {profile_id}: {lang}")
                
                submit_resp = api.put("/profiles/detect", json={"profile_id": profile_id, "language_code": lang})
                submit_resp.raise_for_status()
                logger.info(f"Successfully uploaded detection result for profile ID {profile_id}")
                return True
        except Exception as e:
            logger.error(f"Error during profile detection task processing: {e}")

        # 2. Fallback to claiming job task
        logger.info("Polling for pending detection jobs...")
        try:
            resp = api.post("/jobs/claim-detect", json={"agent_name": args.name})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error polling API: {e}")
            return False

        data = resp.json()
        job_data = data.get("job")

        if not job_data:
            logger.info("No pending jobs available for language detection.")
            return False

        job_title = job_data.get("title")
        job_url = job_data.get("url")
        job_description = job_data.get("description") or ""
        job_requirements = job_data.get("requirements") or ""

        logger.info(f"Successfully claimed job: {job_title} ({job_url})")

        # Concatenate title, description, and requirements to perform language detection
        text_for_detection = f"{job_title}\n{job_description}\n{job_requirements}"

        try:
            lang = detector.detect_lang(text_for_detection)
            logger.info(f"Detected language for '{job_title}': {lang}")

            submit_resp = api.put(
                "/jobs/detect", json={"url": job_url, "language_code": lang}
            )
            submit_resp.raise_for_status()
            logger.info("Successfully uploaded detection result")

        except Exception as e:
            logger.error(f"Error during detection processing or upload: {e}")
        return True

    try:
        run_agent_loop(cycle, default_interval=10.0)
    finally:
        api.close()


if __name__ == "__main__":
    run()
