import os

from core.infrastructure.http.http_client import HttpClient
from core.infrastructure.logging.logger import get_logger
from core.utils.agent import get_agent_name
from core.utils.api import make_api_client
from dotenv import load_dotenv

from abg_discovery.scraper import AbgDiscovery

load_dotenv()


def get_config() -> dict:
    max_pages = int(os.environ.get("MAX_PAGES", "5"))
    return {"max_pages": max_pages}


def run():
    agent_name = get_agent_name("abg-discovery-worker")
    logger = get_logger(agent_name)
    config = get_config()
    api = make_api_client(timeout=30.0)

    http = HttpClient()
    scraper = AbgDiscovery(http, max_pages=config["max_pages"])

    logger.info(f"Starting ABG crawler discovery agent (name: {agent_name})")

    def cycle() -> bool:
        logger.info("Fetching recent known URLs to optimize insertion...")
        known_resp = api.get(f"/jobs/urls?source={scraper.SOURCE_NAME}&limit=500")
        known_resp.raise_for_status()
        known_urls = set(known_resp.json().get("urls", []))

        logger.info(f"Loaded {len(known_urls)} recent known URLs from API")
        new_jobs = scraper.search_all(known_urls)

        if not new_jobs:
            logger.info("No listings found in this cycle")
            return False

        found_urls = [j.url for j in new_jobs]
        check_resp = api.post("/jobs/known-urls", json={"urls": found_urls})
        check_resp.raise_for_status()
        already_known = set(check_resp.json().get("known_urls", []))

        truly_new = [j for j in new_jobs if j.url not in already_known]
        logger.info(f"Found {len(new_jobs)} listings, {len(truly_new)} are truly new")

        if truly_new:
            stubs = [{"title": j.title, "url": j.url, "source": j.source} for j in truly_new]
            resp = api.post("/jobs", json=stubs)
            resp.raise_for_status()
            logger.info(f"Submitted {len(truly_new)} new job stubs to API")

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
