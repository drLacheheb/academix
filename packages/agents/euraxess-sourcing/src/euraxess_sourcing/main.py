import os

from core.infrastructure.http.http_client import HttpClient
from core.infrastructure.logging.logger import get_logger
from core.utils.agent import get_agent_name
from core.utils.api import make_api_client
from dotenv import load_dotenv

from euraxess_sourcing.scraper import EuraxessSourcing

load_dotenv()


def run():
    agent_name = get_agent_name("euraxess-sourcing-worker")
    logger = get_logger(agent_name)
    api = make_api_client(timeout=30.0)

    http = HttpClient()
    scraper = EuraxessSourcing(http)

    logger.info(f"Starting EURAXESS crawler sourcing agent (name: {agent_name})")

    def cycle() -> bool:
        logger.info("Checking for jobs needing detail scraping...")
        pending_resp = api.get(f"/jobs/pending-details?source={scraper.SOURCE_NAME}")
        pending_resp.raise_for_status()
        pending_jobs = pending_resp.json()

        if not pending_jobs:
            logger.info("All EURAXESS jobs are fully scraped. Nothing to do.")
            return False

        logger.info(f"Fetching details for {len(pending_jobs)} jobs...")
        updates = []
        for idx, job_data in enumerate(pending_jobs, 1):
            job_title = job_data.get("title")
            job_url = job_data.get("url")
            logger.info(f"[{idx}/{len(pending_jobs)}] Fetching: {job_title}")

            try:
                detail_update = scraper.source_detail(job_url)

                if not detail_update.job_details:
                    detail_update.job_details = (
                        f"[EXPIRED] This job posting is no longer available. (Title: {job_title})"
                    )

                updates.append(detail_update.model_dump())
            except Exception as scrape_err:
                logger.error(
                    f"Failed scraping details for job '{job_title}' ({job_url}): {scrape_err}"
                )

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

            crawl_interval = float(os.environ.get("SOURCING_INTERVAL", "15.0"))
            run_agent_loop(cycle, default_interval=crawl_interval)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
