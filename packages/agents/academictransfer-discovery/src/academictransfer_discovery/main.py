import os
import httpx
from dotenv import load_dotenv

from core.http_client import HttpClient
from core.logging import get_logger
from academictransfer_discovery.scraper import AcademicTransferDiscovery

load_dotenv()

logger = get_logger("academictransfer-discovery")


def get_config() -> dict:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_token = os.environ.get("API_TOKEN", "")
    max_pages = int(os.environ.get("MAX_PAGES", "5"))
    return {"api_url": api_url, "api_token": api_token, "max_pages": max_pages}


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
    scraper = AcademicTransferDiscovery(http, max_pages=config["max_pages"])

    logger.info("Starting AcademicTransfer crawler discovery agent")

    try:
        logger.info("Starting broad search (newest first)...")
        known_urls: set[str] = set()
        new_jobs = scraper.search_all(known_urls)

        if new_jobs:
            found_urls = [j.url for j in new_jobs]
            check_resp = api.post("/jobs/known-urls", json={"urls": found_urls})
            check_resp.raise_for_status()
            already_known = set(check_resp.json().get("known_urls", []))

            truly_new = [j for j in new_jobs if j.url not in already_known]
            logger.info(f"Found {len(new_jobs)} listings, {len(truly_new)} are truly new")

            if truly_new:
                stubs = [
                    {"title": j.title, "url": j.url, "source": j.source, "keywords": j.keywords}
                    for j in truly_new
                ]
                resp = api.post("/jobs", json=stubs)
                resp.raise_for_status()
                logger.info(f"Submitted {len(truly_new)} new job stubs to API")

        logger.info("AcademicTransfer crawler discovery agent finished successfully")

    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
