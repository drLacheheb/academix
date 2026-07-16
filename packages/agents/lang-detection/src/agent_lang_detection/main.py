import argparse
import os
import time
import httpx
from dotenv import load_dotenv

from core.logging import get_logger
from agent_lang_detection.detector import LanguageDetector

load_dotenv()


def get_config() -> dict:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_token = os.environ.get("API_TOKEN", "")
    return {
        "api_url": api_url,
        "api_token": api_token,
    }


def make_api_client(config: dict) -> httpx.Client:
    return httpx.Client(
        base_url=config["api_url"],
        headers={"Authorization": f"Bearer {config['api_token']}"},
        timeout=60.0,
    )


def run():
    parser = argparse.ArgumentParser(description="Job Language Detection Agent")
    parser.add_argument(
        "--name",
        type=str,
        default=os.environ.get("AGENT_NAME", "lang-detect-worker"),
        help="Custom agent identifier for locking",
    )
    args = parser.parse_args()

    logger = get_logger(args.name)
    config = get_config()

    logger.info(f"Starting Language Detection Agent (name: {args.name})")

    detector = LanguageDetector()
    api = make_api_client(config)

    try:
        while True:
            logger.info("Polling for pending detection jobs...")
            try:
                resp = api.post("/jobs/claim-detect", json={"agent_name": args.name})
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling API: {e}")
                time.sleep(10)
                continue

            data = resp.json()
            job_data = data.get("job")

            if not job_data:
                logger.info("No pending jobs available. Detection batch completed. Exiting.")
                break

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

                submit_resp = api.put("/jobs/detect", json={
                    "url": job_url,
                    "language_code": lang
                })
                submit_resp.raise_for_status()
                logger.info("Successfully uploaded detection result")

            except Exception as e:
                logger.error(f"Error during detection processing or upload: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Agent shutting down due to KeyboardInterrupt")
    finally:
        api.close()


if __name__ == "__main__":
    run()
