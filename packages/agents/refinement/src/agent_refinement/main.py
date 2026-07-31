import os

from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.embedding_service import EmbeddingService
from core.utils.agent import get_agent_name, run_agent_loop
from core.utils.api import make_api_client
from dotenv import load_dotenv

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
    agent_name = get_agent_name("refinement-worker")
    logger = get_logger(agent_name)
    config = get_config()
    embedding_service = EmbeddingService()

    logger.info(f"Starting Job Refinement Agent (name: {agent_name})")

    from core.infrastructure.services.http_runner import HttpLlmRunner

    runner = HttpLlmRunner()
    refiner = LlmRefiner(
        runner=runner,
        max_text_chars=config["max_text_chars"],
    )

    from core.domain.models.profile import CandidateProfile

    api = make_api_client(timeout=60.0)

    def load_refiner_if_needed():
        pass

    def cycle() -> bool:
        nonlocal refiner, api, logger
        # 1. Try to claim candidate profile refinement task
        profile_data = None
        try:
            profile_resp = api.post("/profiles/claim-refine", json={"agent_name": agent_name})
            profile_resp.raise_for_status()
            profile_data = profile_resp.json().get("profile")
        except Exception as e:
            logger.error(f"Error polling profile refinement task from API: {e}")

        if profile_data:
            profile_id = profile_data["id"]
            try:
                raw_text = profile_data.get("raw_text_en") or profile_data.get("raw_text") or ""
                logger.info(
                    f"Successfully claimed candidate profile for refinement: ID {profile_id}"
                )

                has_structured_fields = bool(
                    profile_data.get("skills")
                    or profile_data.get("highest_degree")
                    or profile_data.get("research_interests")
                )

                if has_structured_fields or not raw_text:
                    logger.info(
                        f"[{profile_id}] Profile has pre-existing structured fields. "
                        f"Encoding embeddings directly..."
                    )
                    profile = CandidateProfile.from_dict(profile_data)
                else:
                    load_refiner_if_needed()
                    logger.info("Running LLM skills and metadata extraction...")
                    extracted = refiner.refine_cv(raw_text)

                    # Merge with metadata from candidate upload if any
                    extracted["cv_file_path"] = profile_data.get("cv_file_path")
                    if not extracted.get("name") and profile_data.get("name"):
                        extracted["name"] = profile_data.get("name")
                    if not extracted.get("email") and profile_data.get("email"):
                        extracted["email"] = profile_data.get("email")

                    profile = CandidateProfile.from_dict(extracted)

                profile.skill_embedding = embedding_service.encode_skills(profile.skills or [])
                profile.research_embedding = embedding_service.encode_research(
                    profile.research_interests or []
                )

                logger.info("Finished CV refinement. Submitting results to API...")
                submit_resp = api.put(
                    "/profiles/refine",
                    json={
                        "profile_id": profile_id,
                        "profile": profile.to_dict(),
                    },
                )
                submit_resp.raise_for_status()
                logger.info("Successfully uploaded profile refinement results")
            except Exception as e:
                logger.error(f"Error during profile refinement processing for ID {profile_id}: {e}")
            return True

        # 2. Fallback to claiming job task
        logger.info("Polling for pending refinement jobs...")
        try:
            resp = api.post("/jobs/claim-refine", json={"agent_name": agent_name})
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
        job_requirements = job_data.get("requirements_en") or job_data.get("requirements")

        logger.info(f"Successfully claimed job: {job_title} ({job_url})")

        load_refiner_if_needed()

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

            result.skill_embedding = embedding_service.encode_skills(result.required_skills or [])
            result.research_embedding = embedding_service.encode_research(
                result.required_skills or [],
                title=job_title,
            )

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
