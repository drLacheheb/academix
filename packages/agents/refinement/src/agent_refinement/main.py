from core.domain.models.profile import CandidateProfile
from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.instructor_client import InstructorLlmClient
from core.usecases.cv_extraction import ExtractCvUseCase
from core.usecases.job_refinement_llm import RefineJobUseCase
from core.utils.agent import get_agent_name, run_agent_loop
from core.utils.api import make_api_client
from dotenv import load_dotenv

load_dotenv()


def run():
    agent_name = get_agent_name("refinement-worker")
    logger = get_logger(agent_name)

    logger.info(f"Starting Job Refinement Agent (name: {agent_name})")

    client = InstructorLlmClient()
    cv_extractor = ExtractCvUseCase(llm=client)
    job_refiner = RefineJobUseCase(llm=client)

    api = make_api_client(timeout=60.0)

    def cycle() -> bool:
        nonlocal cv_extractor, job_refiner, api, logger
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

                def _is_valid_field(val) -> bool:
                    if not val:
                        return False
                    if isinstance(val, str) and val.strip().lower() in ("none", "null", "[]", "{}"):
                        return False
                    if isinstance(val, list) and len(val) == 0:
                        return False
                    return True

                has_structured_fields = (
                    _is_valid_field(profile_data.get("skills"))
                    or _is_valid_field(profile_data.get("highest_degree"))
                    or _is_valid_field(profile_data.get("research_interests"))
                )

                if has_structured_fields or not raw_text:
                    logger.info(
                        f"[{profile_id}] Profile has pre-existing structured fields. "
                        f"Passing to embedding stage..."
                    )
                    profile = CandidateProfile.from_dict(profile_data)
                else:
                    logger.info("Running LLM skills and metadata extraction...")
                    extracted = cv_extractor.execute(raw_text)
                    extracted_dict = extracted.model_dump()

                    # Merge with metadata from candidate upload if any
                    extracted_dict["cv_file_path"] = profile_data.get("cv_file_path")
                    if not extracted_dict.get("name") and profile_data.get("name"):
                        extracted_dict["name"] = profile_data.get("name")
                    if not extracted_dict.get("email") and profile_data.get("email"):
                        extracted_dict["email"] = profile_data.get("email")

                    profile = CandidateProfile.from_dict(extracted_dict)

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
            return False

        job_title = job_data.get("title")
        job_url = job_data.get("url")
        job_details = job_data.get("job_details_en") or job_data.get("job_details")

        logger.info(f"Successfully claimed job: {job_title} ({job_url})")

        try:
            result = job_refiner.execute(
                url=job_url,
                title=job_title,
                job_details=job_details,
            )

            logger.info(f"Refinement completed for {job_title}")
            logger.info(f"  -> Skills: {result.required_skills}")
            logger.info(f"  -> Research Interests: {result.research_interests}")
            logger.info(f"  -> Degree Fields: {result.degree_fields}")
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
        api.close()


if __name__ == "__main__":
    run()
