from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.embedding_service import EmbeddingService
from core.utils.agent import get_agent_name, run_agent_loop
from core.utils.api import make_api_client
from dotenv import load_dotenv

load_dotenv()


def run():
    agent_name = get_agent_name("embedding-worker")
    logger = get_logger(agent_name)
    embedding_service = EmbeddingService()

    logger.info(f"Starting Embedding Worker Agent (name: {agent_name})")

    api = make_api_client(timeout=60.0)

    def cycle() -> bool:
        nonlocal api, logger, embedding_service

        # 1. Try to claim candidate profile embedding task
        profile_data = None
        try:
            profile_resp = api.post("/profiles/claim-embed", json={"agent_name": agent_name})
            profile_resp.raise_for_status()
            profile_data = profile_resp.json().get("profile")
        except Exception as e:
            logger.error(f"Error polling profile embedding task from API: {e}")

        if profile_data:
            profile_id = profile_data["id"]
            try:
                logger.info(
                    f"Successfully claimed candidate profile for embedding: ID {profile_id}"
                )
                skills = profile_data.get("skills") or []
                research_interests = profile_data.get("research_interests") or []
                degree_fields = profile_data.get("degree_fields") or []

                skill_emb = embedding_service.encode_skills(skills)
                research_emb = embedding_service.encode_research(research_interests)
                degree_emb = embedding_service.encode_degree(degree_fields)

                logger.info(f"[{profile_id}] Generated profile embeddings. Submitting to API...")
                submit_resp = api.put(
                    "/profiles/complete-embed",
                    json={
                        "profile_id": profile_id,
                        "skill_embedding": skill_emb,
                        "research_embedding": research_emb,
                        "degree_embedding": degree_emb,
                    },
                )
                submit_resp.raise_for_status()
                logger.info(f"[{profile_id}] Successfully uploaded profile embeddings")
            except Exception as e:
                logger.error(f"Error during profile embedding processing for ID {profile_id}: {e}")
            return True

        # 2. Fallback to claiming job embedding task
        logger.info("Polling for pending embedding jobs...")
        try:
            resp = api.post("/jobs/claim-embed", json={"agent_name": agent_name})
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Error polling API: {e}")
            return False

        data = resp.json()
        job_data = data.get("job")

        if not job_data:
            logger.info("No pending jobs available for embedding.")
            return False

        job_title = job_data.get("title", "")
        job_url = job_data.get("url")
        required_skills = job_data.get("required_skills") or []
        research_interests = job_data.get("research_interests") or []
        degree_fields = job_data.get("degree_fields") or []

        logger.info(f"Successfully claimed job for embedding: {job_title} ({job_url})")

        try:
            skill_emb = embedding_service.encode_skills(required_skills)
            research_emb = embedding_service.encode_research(research_interests, title=job_title)
            degree_emb = embedding_service.encode_degree(degree_fields)

            logger.info(f"[{job_title}] Generated job embeddings. Submitting to API...")
            submit_resp = api.put(
                "/jobs/embed",
                json={
                    "url": job_url,
                    "skill_embedding": skill_emb,
                    "research_embedding": research_emb,
                    "degree_embedding": degree_emb,
                },
            )
            submit_resp.raise_for_status()
            logger.info(f"Successfully uploaded embedding results for {job_title}")

        except Exception as e:
            logger.error(f"Error during embedding processing or upload for {job_url}: {e}")
        return True

    try:
        run_agent_loop(cycle, default_interval=10.0)
    finally:
        api.close()


if __name__ == "__main__":
    run()
