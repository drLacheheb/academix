import os

from core.domain.models.job import Job
from core.domain.models.profile import CandidateProfile
from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.instructor_client import InstructorLlmClient
from core.usecases.match_explanation import ExplainMatchUseCase
from core.usecases.match_scorer import MatchScorer
from core.utils.agent import get_agent_name, run_agent_loop
from core.utils.api import make_api_client
from dotenv import load_dotenv

load_dotenv()


def get_config() -> dict:
    match_threshold = float(os.environ.get("MATCH_THRESHOLD", "0.7"))
    return {
        "match_threshold": match_threshold,
    }


def run():
    agent_name = get_agent_name("matching-worker")
    logger = get_logger(agent_name)
    config = get_config()

    logger.info(f"Starting Job Matching Agent (name: {agent_name})")

    client = InstructorLlmClient()
    explainer = ExplainMatchUseCase(llm=client)

    api = make_api_client(timeout=60.0)

    def cycle() -> bool:
        nonlocal explainer, api, logger
        logger.info("Polling for pending matching tasks...")
        task_processed = False

        try:
            resp = api.post("/matches/claim", json={"agent_name": agent_name})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error polling matching tasks: {e}")
            return False

        task_data = resp.json().get("task")
        if task_data:
            task_processed = True
            task_id = task_data["id"]
            entity_type = task_data["entity_type"]
            entity_id = task_data["entity_id"]

            logger.info(f"Claimed matching task {task_id}: {entity_type} {entity_id}")

            try:
                matches_list = []
                if entity_type == "candidate":
                    # Load candidate profile
                    profile_resp = api.get(f"/profiles/{entity_id}")
                    profile_resp.raise_for_status()
                    candidate = CandidateProfile.from_dict(profile_resp.json())

                    # Load all refined jobs
                    jobs_resp = api.get("/jobs/refined")
                    jobs_resp.raise_for_status()
                    refined_jobs = [Job.from_dict(j) for j in jobs_resp.json()]

                    # Score candidate against all jobs
                    for job in refined_jobs:
                        match = MatchScorer.score_candidate_against_job(
                            candidate, job, threshold=config["match_threshold"]
                        )
                        if match:
                            matches_list.append(match)

                elif entity_type == "job":
                    # Load all refined jobs to find this specific one
                    jobs_resp = api.get("/jobs/refined")
                    jobs_resp.raise_for_status()
                    job_dict = next((j for j in jobs_resp.json() if j["url"] == entity_id), None)

                    if not job_dict:
                        raise ValueError(f"Refined job not found: {entity_id}")

                    job = Job.from_dict(job_dict)

                    # Load all profiles
                    profiles_resp = api.get("/profiles")
                    profiles_resp.raise_for_status()
                    candidates = [
                        CandidateProfile.from_dict(p)
                        for p in profiles_resp.json()
                        if p.get("status") == "COMPLETED"
                    ]

                    # Score job against all candidates
                    for candidate in candidates:
                        match = MatchScorer.score_candidate_against_job(
                            candidate, job, threshold=config["match_threshold"]
                        )
                        if match:
                            matches_list.append(match)

                # Submit matches
                payload_matches = [
                    {
                        "candidate_id": m.candidate_id,
                        "job_url": m.job_url,
                        "score": m.score,
                        "degree_eligible": m.degree_eligible,
                        "language_eligible": m.language_eligible,
                        "skill_score": m.skill_score,
                        "research_score": m.research_score,
                    }
                    for m in matches_list
                ]
                submit_resp = api.put(
                    "/matches/complete",
                    json={"task_id": task_id, "matches": payload_matches},
                )
                submit_resp.raise_for_status()
                logger.info(
                    f"Successfully processed matching task {task_id} with "
                    f"{len(payload_matches)} matches saved."
                )

            except Exception as e:
                logger.error(f"Error processing matching task {task_id}: {e}")
                try:
                    api.put(f"/matches/fail/{task_id}")
                except Exception:
                    pass
            return True

        # Check if match explanations are enabled
        enable_explanations = os.environ.get("ENABLE_MATCH_EXPLANATION", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        if enable_explanations:
            # Polling for explanations
            logger.info("Polling for pending match explanations...")
            try:
                explain_resp = api.post("/matches/claim-explain", json={"agent_name": agent_name})
                explain_resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling match explanations: {e}")
                return False

            match_data = explain_resp.json().get("match")
            if match_data:
                task_processed = True
                match_id = match_data["id"]
                candidate_id = match_data["candidate_id"]
                job_url = match_data["job_url"]

                logger.info(
                    f"Claimed match explanation {match_id} for candidate "
                    f"{candidate_id} and job {job_url}"
                )

                try:
                    # Load candidate profile
                    profile_resp = api.get(f"/profiles/{candidate_id}")
                    profile_resp.raise_for_status()
                    candidate = CandidateProfile.from_dict(profile_resp.json())

                    # Load jobs list to find job details
                    jobs_resp = api.get("/jobs/refined")
                    jobs_resp.raise_for_status()
                    job_dict = next((j for j in jobs_resp.json() if j["url"] == job_url), None)
                    if not job_dict:
                        raise ValueError(f"Job not found for explanation: {job_url}")
                    job = Job.from_dict(job_dict)

                    # Generate explanation using domain usecase
                    explanation = explainer.execute(candidate, job)
                    logger.info(f"Generated explanation: {explanation}")

                    # Submit explanation
                    submit_resp = api.put(
                        "/matches/complete-explain",
                        json={"match_id": match_id, "explanation": explanation},
                    )
                    submit_resp.raise_for_status()
                    logger.info(f"Successfully submitted explanation for match {match_id}.")

                except Exception as e:
                    logger.error(f"Failed to generate/submit explanation for match {match_id}: {e}")
                    try:
                        api.put(f"/matches/fail-explain/{match_id}")
                    except Exception:
                        pass
                return True

        # If no tasks or explanations were processed
        if not task_processed:
            logger.info("No matching tasks or pending explanations available.")
        return False

    try:
        run_agent_loop(cycle, default_interval=15.0)
    finally:
        api.close()


if __name__ == "__main__":
    run()
