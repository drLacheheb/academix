import argparse
import os
import sys
from dotenv import load_dotenv

from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from agent_refinement.llm_refiner import LlmRefiner

load_dotenv()


def get_config() -> dict:
    model_path = os.environ.get(
        "MODEL_PATH",
        "unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf",
    )
    models_dir = os.environ.get("MODELS_DIR", "models")
    max_length = int(os.environ.get("MAX_LENGTH", "4096"))
    temperature = float(os.environ.get("TEMPERATURE", "0.0"))
    max_text_chars = int(os.environ.get("MAX_TEXT_CHARS", "3000"))
    return {
        "model_path": model_path,
        "models_dir": models_dir,
        "max_length": max_length,
        "temperature": temperature,
        "max_text_chars": max_text_chars,
    }


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
        models_dir=config["models_dir"],
        max_length=config["max_length"],
        temperature=config["temperature"],
        max_text_chars=config["max_text_chars"],
    )

    api = make_api_client(timeout=60.0)

    from core.utils.agent import run_agent_loop

    def cycle() -> bool:
        nonlocal refiner, api, args, logger
        logger.info("Polling for pending refinement jobs...")
        try:
            resp = api.post("/jobs/claim-refine", json={"agent_name": args.name})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error polling API: {e}")
            return False

        data = resp.json()
        job_data = data.get("job")

        if not job_data:
            logger.info("No pending jobs available for refinement.")
            if refiner.is_loaded:
                refiner.free_model()
            return False

        job_title = job_data.get("title")
        job_url = job_data.get("url")
        job_location = job_data.get("location")
        job_description = job_data.get("description_en") or job_data.get("description")
        job_requirements = job_data.get("requirements_en") or job_data.get(
            "requirements"
        )

        logger.info(f"Successfully claimed job: {job_title} ({job_url})")

        if not refiner.is_loaded:
            logger.info("First job claimed. Loading GGUF model into memory...")
            try:
                refiner.load_model()
            except Exception as e:
                logger.error(f"Failed to load GGUF model: {e}")
                sys.exit(1)

        try:
            result = refiner.refine(
                url=job_url,
                title=job_title,
                location=job_location,
                description=job_description,
                requirements=job_requirements,
            )

            logger.info(f"Refinement completed for {job_title}")
            logger.info(f"  -> Skills: {result.required_skills}")
            logger.info(f"  -> Education: {result.education_level}")

            submit_resp = api.put("/jobs/refine", json=result.model_dump())
            submit_resp.raise_for_status()
            logger.info("Successfully uploaded refinement results")

        except Exception as e:
            logger.error(f"Error during refinement processing or upload: {e}")
        return True

    try:
        run_agent_loop(cycle, default_interval=10.0)
    finally:
        if refiner.is_loaded:
            refiner.free_model()
        api.close()


if __name__ == "__main__":
    run()
