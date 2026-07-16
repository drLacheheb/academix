import argparse
import os
import time
import httpx
from dotenv import load_dotenv

from core.models.job import Job
from core.logging import get_logger
from agent_refinement.llm_refiner import LlmRefiner

load_dotenv()


def get_config() -> dict:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_token = os.environ.get("API_TOKEN", "")
    model_path = os.environ.get(
        "MODEL_PATH",
        "phi-4-mini-onnx/cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4",
    )
    max_length = int(os.environ.get("MAX_LENGTH", "4096"))
    temperature = float(os.environ.get("TEMPERATURE", "0.0"))
    max_text_chars = int(os.environ.get("MAX_TEXT_CHARS", "3000"))
    return {
        "api_url": api_url,
        "api_token": api_token,
        "model_path": model_path,
        "max_length": max_length,
        "temperature": temperature,
        "max_text_chars": max_text_chars,
    }


def make_api_client(config: dict) -> httpx.Client:
    return httpx.Client(
        base_url=config["api_url"],
        headers={"Authorization": f"Bearer {config['api_token']}"},
        timeout=60.0,
    )


def run():
    parser = argparse.ArgumentParser(description="Job Refinement Agent")
    parser.add_argument(
        "--name",
        type=str,
        default=os.environ.get("AGENT_NAME", "refinement-worker"),
        help="Custom agent identifier for locking",
    )
    args = parser.parse_args()

    logger = get_logger(args.name)
    config = get_config()

    logger.info(f"Starting Job Refinement Agent (name: {args.name})")

    refiner = LlmRefiner(
        model_path=config["model_path"],
        max_length=config["max_length"],
        temperature=config["temperature"],
        max_text_chars=config["max_text_chars"],
    )
    model_loaded = False

    api = make_api_client(config)

    try:
        while True:
            logger.info("Polling for pending refinement jobs...")
            try:
                resp = api.post("/jobs/claim-refine", json={"agent_name": args.name})
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling API: {e}")
                time.sleep(10)
                continue

            data = resp.json()
            job_data = data.get("job")

            if not job_data:
                logger.info("No pending jobs available. Refinement batch completed. Exiting.")
                break

            job = Job.from_dict(job_data)
            logger.info(f"Successfully claimed job: {job.title} ({job.url})")

            if not model_loaded:
                logger.info("First job claimed. Loading ONNX model into memory...")
                try:
                    refiner.load_model()
                    model_loaded = True
                except Exception as e:
                    logger.error(f"Failed to load ONNX model: {e}")
                    sys.exit(1)

            try:
                refiner.refine(job)

                logger.info(f"Refinement completed for {job.title}")
                logger.info(f"  -> Skills: {job.required_skills}")
                logger.info(f"  -> Education: {job.education_level}")

                submit_data = {
                    "url": job.url,
                    "required_skills": job.required_skills or [],
                    "education_level": job.education_level,
                }
                submit_resp = api.put("/jobs/refine", json=submit_data)
                submit_resp.raise_for_status()
                logger.info("Successfully uploaded refinement results")

            except Exception as e:
                logger.error(f"Error during refinement processing or upload: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Agent shutting down due to KeyboardInterrupt")
    finally:
        api.close()


if __name__ == "__main__":
    import sys
    run()
