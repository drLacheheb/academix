import os
from dotenv import load_dotenv

from core.infrastructure.http.http_client import HttpClient
from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from academictransfer_sourcing.scraper import AcademicTransferSourcing

load_dotenv()

logger = get_logger("academictransfer-sourcing")


def run():
    api = make_api_client(timeout=30.0)

    http = HttpClient()
    scraper = AcademicTransferSourcing(http)

    logger.info("Starting AcademicTransfer crawler sourcing agent")

    def cycle() -> bool:
        logger.info("Checking for jobs needing detail scraping...")
        pending_resp = api.get(f"/jobs/pending-details?source={scraper.SOURCE_NAME}")
        pending_resp.raise_for_status()
        pending_jobs = pending_resp.json()

        if not pending_jobs:
            logger.info("All AcademicTransfer jobs are fully scraped. Nothing to do.")
            return False

        logger.info(f"Fetching details for {len(pending_jobs)} jobs...")
        updates = []
        for idx, job_data in enumerate(pending_jobs, 1):
            job_title = job_data.get("title")
            job_url = job_data.get("url")
            logger.info(f"[{idx}/{len(pending_jobs)}] Fetching: {job_title}")

            detail_update = scraper.source_detail(job_url)

            if not detail_update.description:
                detail_update.description = f"[EXPIRED] This job posting is no longer available. (Title: {job_title})"
                if not detail_update.requirements:
                    detail_update.requirements = "None"

            updates.append(detail_update.model_dump())

        if updates:
            logger.info(f"Uploading {len(updates)} updates to API...")
            resp = api.put("/jobs/details", json=updates)
            resp.raise_for_status()
        return True

    try:
        crawl_once = os.environ.get("CRAWL_ONCE", "false").lower() == "true"
        if crawl_once:
            cycle()
        else:
            from core.utils.agent import run_agent_loop
            crawl_interval = float(os.environ.get("CRAWL_INTERVAL", "15.0"))
            run_agent_loop(cycle, default_interval=crawl_interval)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
