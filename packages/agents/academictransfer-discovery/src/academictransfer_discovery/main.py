import os

from core.infrastructure.http.http_client import HttpClient
from core.infrastructure.logging.logger import get_logger
from core.utils.agent import get_agent_name
from core.utils.api import make_api_client
from dotenv import load_dotenv

from academictransfer_discovery.scraper import AcademicTransferDiscovery

load_dotenv()


def run():
    agent_name = get_agent_name("academictransfer-discovery-worker")
    logger = get_logger(agent_name)
    api = make_api_client(timeout=30.0)

    http = HttpClient()
    scraper = AcademicTransferDiscovery(http)

    logger.info(f"Starting AcademicTransfer XML Sitemap discovery agent (name: {agent_name})")

    def cycle() -> bool:
        logger.info("Fetching all active job URLs from AcademicTransfer XML sitemap...")
        all_jobs = scraper.fetch_all_jobs_from_sitemap()

        if not all_jobs:
            logger.warning("No jobs retrieved from sitemap XML")
            return False

        found_urls = [j.url for j in all_jobs]
        check_resp = api.post("/jobs/known-urls", json={"urls": found_urls})
        check_resp.raise_for_status()
        already_known = set(check_resp.json().get("known_urls", []))

        truly_new = [j for j in all_jobs if j.url not in already_known]
        logger.info(f"Retrieved {len(all_jobs)} total sitemap jobs, {len(truly_new)} are truly new")

        if truly_new:
            stubs = [{"title": j.title, "url": j.url, "source": j.source} for j in truly_new]
            resp = api.post("/jobs", json=stubs)
            resp.raise_for_status()
            logger.info(f"Submitted {len(truly_new)} new job stubs to API")

        # Always update checkpoint to newest job URL found in sitemap
        checkpoint_payload = {
            "source": scraper.SOURCE_NAME,
            "url": all_jobs[0].url,
        }
        update_resp = api.put("/jobs/checkpoint", json=checkpoint_payload)
        update_resp.raise_for_status()
        logger.info(f"Updated crawler checkpoint to: {all_jobs[0].url}")

        return len(truly_new) > 0

    try:
        crawl_once = os.environ.get("CRAWL_ONCE", "false").lower() == "true"
        if crawl_once:
            cycle()
        else:
            from core.utils.agent import run_agent_loop

            crawl_interval = float(os.environ.get("CRAWL_INTERVAL", "21600.0"))
            run_agent_loop(cycle, default_interval=crawl_interval)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
