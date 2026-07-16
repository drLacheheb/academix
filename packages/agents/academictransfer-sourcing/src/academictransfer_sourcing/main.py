import os
import httpx
from dotenv import load_dotenv

from core.http_client import HttpClient
from core.logging import get_logger
from academictransfer_sourcing.scraper import AcademicTransferSourcing

load_dotenv()

logger = get_logger("academictransfer-sourcing")


def get_config() -> dict:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_token = os.environ.get("API_TOKEN", "")
    return {"api_url": api_url, "api_token": api_token}


def make_api_client(config: dict) -> httpx.Client:
    return httpx.Client(
        base_url=config["api_url"],
        headers={"Authorization": f"Bearer {config['api_token']}"},
        timeout=30.0,
    )


def run():
    config = get_config()
    api = make_api_client(config)

    http = HttpClient()
    scraper = AcademicTransferSourcing(http)

    logger.info("Starting AcademicTransfer crawler sourcing agent")

    try:
        logger.info("Checking for jobs needing detail scraping...")
        pending_resp = api.get(f"/jobs/pending-details?source={scraper.SOURCE_NAME}")
        pending_resp.raise_for_status()
        pending_jobs = pending_resp.json()

        if not pending_jobs:
            logger.info("All AcademicTransfer jobs are fully scraped. Nothing to do.")
        else:
            logger.info(f"Fetching details for {len(pending_jobs)} jobs...")
            for idx, job_data in enumerate(pending_jobs, 1):
                from core.models.job import Job
                job = Job.from_dict(job_data)
                logger.info(f"[{idx}/{len(pending_jobs)}] Fetching: {job.title}")

                scraper.enrich_detail(job)

                if job.description:
                    detail_update = {
                        "url": job.url,
                        "description": job.description,
                        "requirements": job.requirements,
                        "deadline": job.deadline,
                        "employer": job.employer,
                        "location": job.location,
                    }
                    resp = api.put("/jobs/details", json=[detail_update])
                    resp.raise_for_status()

        logger.info("AcademicTransfer crawler sourcing agent finished successfully")

    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
