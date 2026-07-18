import argparse
import os
import time
from dotenv import load_dotenv

from core.infrastructure.logging.logger import get_logger
from core.domain.models.profile import CandidateProfile
from core.domain.models.job import Job
from core.usecases.match_scorer import MatchScorer
from core.infrastructure.services.llm_runner import LocalLlmRunner
from core.domain.interfaces.services import BaseLlmRunner
from core.utils.api import make_api_client

load_dotenv()


def get_config() -> dict:
    model_path = os.environ.get(
        "MODEL_PATH",
        "unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf",
    )
    models_dir = os.environ.get("MODELS_DIR", "models")
    max_length = int(os.environ.get("MAX_LENGTH", "4096"))
    temperature = float(os.environ.get("TEMPERATURE", "0.0"))
    match_threshold = float(os.environ.get("MATCH_THRESHOLD", "0.7"))
    return {
        "model_path": model_path,
        "models_dir": models_dir,
        "max_length": max_length,
        "temperature": temperature,
        "match_threshold": match_threshold,
    }


class LlmExplainer:
    def __init__(self, runner: BaseLlmRunner):
        self._runner = runner

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "match_explanation_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    @property
    def is_loaded(self) -> bool:
        return self._runner.is_loaded

    def load_model(self, logger) -> None:
        self._runner.load_model()

    def free_model(self, logger) -> None:
        self._runner.free_model()

    def generate_explanation(self, candidate: CandidateProfile, job: Job) -> str:
        prompt = self._system_prompt.format(
            candidate_name=candidate.name,
            highest_degree=candidate.highest_degree or "None",
            candidate_skills=", ".join(candidate.skills or []),
            research_interests=", ".join(candidate.research_interests or []),
            job_title=job.title,
            job_skills=", ".join(job.required_skills or []),
            job_education=job.education_level or "None",
        )

        raw_output = self._runner.create_chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Write the explanation paragraph matching {candidate.name} with '{job.title}'.",
                },
            ],
            max_tokens=256,
        )
        return raw_output


def run():
    parser = argparse.ArgumentParser(description="Job Matching Agent")
    parser.add_argument(
        "--name",
        type=str,
        default=os.environ.get("AGENT_NAME", "matching-worker"),
        help="Custom agent identifier for locking",
    )
    args = parser.parse_args()

    logger = get_logger(args.name)
    config = get_config()

    logger.info(f"Starting Job Matching Agent (name: {args.name})")

    runner = LocalLlmRunner(
        model_path=config["model_path"],
        models_dir=config["models_dir"],
        max_context=config["max_length"],
        temperature=config["temperature"],
    )
    explainer = LlmExplainer(runner=runner)

    api = make_api_client(timeout=60.0)

    try:
        while True:
            logger.info("Polling for pending matching tasks...")
            task_processed = False

            try:
                resp = api.post("/matches/claim", json={"agent_name": args.name})
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling matching tasks: {e}")
                time.sleep(10)
                continue

            task_data = resp.json().get("task")
            if task_data:
                task_processed = True
                task_id = task_data["id"]
                entity_type = task_data["entity_type"]
                entity_id = task_data["entity_id"]

                logger.info(
                    f"Claimed matching task {task_id}: {entity_type} {entity_id}"
                )

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
                        job_dict = next(
                            (j for j in jobs_resp.json() if j["url"] == entity_id), None
                        )

                        if not job_dict:
                            raise ValueError(f"Refined job not found: {entity_id}")

                        job = Job.from_dict(job_dict)

                        # Load all profiles
                        profiles_resp = api.get("/profiles")
                        profiles_resp.raise_for_status()
                        candidates = [
                            CandidateProfile.from_dict(p) for p in profiles_resp.json()
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
                        f"Successfully processed matching task {task_id} with {len(payload_matches)} matches saved."
                    )

                except Exception as e:
                    logger.error(f"Error processing matching task {task_id}: {e}")
                    try:
                        api.put(f"/matches/fail/{task_id}")
                    except Exception:
                        pass
                    time.sleep(5)

            # Polling for explanations
            logger.info("Polling for pending match explanations...")
            try:
                explain_resp = api.post(
                    "/matches/claim-explain", json={"agent_name": args.name}
                )
                explain_resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling match explanations: {e}")
                time.sleep(10)
                continue

            match_data = explain_resp.json().get("match")
            if match_data:
                task_processed = True
                match_id = match_data["id"]
                candidate_id = match_data["candidate_id"]
                job_url = match_data["job_url"]

                logger.info(
                    f"Claimed match explanation {match_id} for candidate {candidate_id} and job {job_url}"
                )

                try:
                    # Load candidate profile
                    profile_resp = api.get(f"/profiles/{candidate_id}")
                    profile_resp.raise_for_status()
                    candidate = CandidateProfile.from_dict(profile_resp.json())

                    # Load jobs list to find job details
                    jobs_resp = api.get("/jobs/refined")
                    jobs_resp.raise_for_status()
                    job_dict = next(
                        (j for j in jobs_resp.json() if j["url"] == job_url), None
                    )
                    if not job_dict:
                        raise ValueError(f"Job not found for explanation: {job_url}")
                    job = Job.from_dict(job_dict)

                    # Lazy-load LLM model
                    if not explainer.is_loaded:
                        explainer.load_model(logger)

                    # Generate explanation
                    explanation = explainer.generate_explanation(candidate, job)
                    logger.info(f"Generated explanation: {explanation}")

                    # Submit explanation
                    submit_resp = api.put(
                        "/matches/complete-explain",
                        json={"match_id": match_id, "explanation": explanation},
                    )
                    submit_resp.raise_for_status()
                    logger.info(
                        f"Successfully submitted explanation for match {match_id}."
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to generate/submit explanation for match {match_id}: {e}"
                    )
                    try:
                        api.put(f"/matches/fail-explain/{match_id}")
                    except Exception:
                        pass
                    time.sleep(5)

            # If no tasks or explanations were processed, sleep to prevent CPU spin
            if not task_processed:
                logger.info(
                    "No matching tasks or pending explanations available. Sleeping..."
                )
                if explainer.is_loaded:
                    explainer.free_model(logger)
                time.sleep(15)

    except KeyboardInterrupt:
        logger.info("Matching agent shutting down due to KeyboardInterrupt")
        if explainer.is_loaded:
            explainer.free_model(logger)
    finally:
        api.close()


if __name__ == "__main__":
    run()
