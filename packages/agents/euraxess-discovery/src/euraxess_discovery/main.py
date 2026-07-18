import os
from dotenv import load_dotenv

from core.infrastructure.http.http_client import HttpClient
from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from euraxess_discovery.scraper import EuraxessDiscovery

load_dotenv()

logger = get_logger("euraxess-discovery")


def get_config() -> dict:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_token = os.environ.get("API_TOKEN", "")
    max_pages = int(os.environ.get("MAX_PAGES", "5"))
    return {"api_url": api_url, "api_token": api_token, "max_pages": max_pages}


def run():
    config = get_config()
    api = make_api_client(timeout=30.0)

    http = HttpClient()
    scraper = EuraxessDiscovery(http, max_pages=config["max_pages"])

    logger.info("Starting EURAXESS crawler discovery agent")

    try:
        logger.info("Fetching recent known URLs and checkpoint to optimize pagination...")
        known_resp = api.get(f"/jobs/urls?source={scraper.SOURCE_NAME}&limit=500")
        known_resp.raise_for_status()
        known_urls = set(known_resp.json().get("urls", []))

        checkpoint_resp = api.get(f"/jobs/checkpoint?source={scraper.SOURCE_NAME}")
        checkpoint_resp.raise_for_status()
        checkpoint_url = checkpoint_resp.json().get("checkpoint_url")

        logger.info(f"Loaded {len(known_urls)} known URLs. Checkpoint URL: {checkpoint_url}")
        new_jobs = scraper.search_all(known_urls, checkpoint_url=checkpoint_url)

        if new_jobs:
            found_urls = [j.url for j in new_jobs]
            check_resp = api.post("/jobs/known-urls", json={"urls": found_urls})
            check_resp.raise_for_status()
            already_known = set(check_resp.json().get("known_urls", []))

            truly_new = [j for j in new_jobs if j.url not in already_known]
            logger.info(f"Found {len(new_jobs)} listings, {len(truly_new)} are truly new")

            if truly_new:
                stubs = [
                    {"title": j.title, "url": j.url, "source": j.source}
                    for j in truly_new
                ]
                resp = api.post("/jobs", json=stubs)
                resp.raise_for_status()
                logger.info(f"Submitted {len(truly_new)} new job stubs to API")

                # Update crawler checkpoint
                checkpoint_payload = {"source": scraper.SOURCE_NAME, "url": new_jobs[0].url}
                update_resp = api.put("/jobs/checkpoint", json=checkpoint_payload)
                update_resp.raise_for_status()
                logger.info(f"Updated crawler checkpoint to: {new_jobs[0].url}")

        logger.info("EURAXESS crawler discovery agent finished successfully")

    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    finally:
        http.close()
        api.close()


if __name__ == "__main__":
    run()
