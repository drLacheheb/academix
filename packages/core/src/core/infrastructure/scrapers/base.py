from core.domain.interfaces.http import BaseHttpClient
from core.domain.interfaces.scrapers import BaseDiscovery, BaseSourcing
from core.domain.models.job import Job
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.logging.logger import get_logger


class ConcreteDiscovery(BaseDiscovery):
    def __init__(self, http_client: BaseHttpClient, max_pages: int = 5):
        self._http = http_client
        self._max_pages_val = max_pages
        agent_tag = f"{self.SOURCE_NAME.lower().replace(' ', '-')}-discovery"
        self.logger = get_logger(agent_tag)

    def extract_total_count(self, html_content: str) -> int | None:
        return None

    def search_all(
        self,
        known_urls: set[str] | None = None,
        checkpoint_url: str | None = None,
        db_total_count: int | None = None,
    ) -> list[Job]:
        import math
        import os

        all_jobs: list[Job] = []
        seen_urls: set[str] = set()
        page = self._start_page()
        max_pages = self._max_pages()
        max_safety_pages = int(os.environ.get("MAX_SAFETY_PAGES", "500"))

        self.logger.info(
            f"Starting search on {self.SOURCE_NAME} (Delta-Bound + Checkpoint Watermark)..."
        )

        checkpoint_found = False
        lookback_pages_left: int | None = None

        while True:
            if max_pages > 0 and page >= (self._start_page() + max_pages):
                self.logger.info(f"  -> Reached page limit ({max_pages} max pages). Stopping.")
                break

            if page > max_safety_pages:
                self.logger.warning(
                    f"Safety circuit breaker triggered: reached max depth of {max_safety_pages}."
                )
                break

            url = self._build_browse_url(page)
            raw = self._http.fetch(url)
            if not raw:
                self.logger.info(f"  -> Finished: Fetch failed on page {page}.")
                break

            content = raw.decode("utf-8", errors="ignore")
            jobs_on_page = self._parse_search_page(content)

            if not jobs_on_page:
                self.logger.info(f"  -> Finished: No more listings found on page {page}.")
                break

            # Calculate Delta-Bound Max Pages on Page 0/1 if site total count is available
            if db_total_count is not None and page == self._start_page():
                site_total = self.extract_total_count(content)
                if site_total is not None:
                    delta = max(0, site_total - db_total_count)
                    items_per_page = max(1, len(jobs_on_page))
                    calculated_pages = math.ceil(delta / items_per_page)
                    max_pages = calculated_pages + 3  # Add +3 Safety Buffer
                    self.logger.info(
                        f"  -> Delta-bound: site={site_total}, db={db_total_count}, "
                        f"delta={delta} -> page limit set to {max_pages} (+3 safety buffer)"
                    )

            jobs_to_keep: list[Job] = []
            for j in jobs_on_page:
                if j.url in seen_urls:
                    continue
                seen_urls.add(j.url)

                if checkpoint_url and j.url == checkpoint_url and not checkpoint_found:
                    self.logger.info(
                        f"  -> Found checkpoint URL: {checkpoint_url}. Lookback buffer active."
                    )
                    checkpoint_found = True
                    lookback_pages_left = 1

                jobs_to_keep.append(j)

            all_jobs.extend(jobs_to_keep)
            self.logger.info(
                f"  -> Page {page}: Found {len(jobs_on_page)} listings ({len(jobs_to_keep)} unique)"
            )

            if lookback_pages_left is not None:
                if lookback_pages_left <= 0:
                    self.logger.info(
                        "  -> Completed 1-page lookback buffer scan. Stopping pagination."
                    )
                    break
                lookback_pages_left -= 1

            page += 1

        return all_jobs

    def _start_page(self) -> int:
        return 1

    def _max_pages(self) -> int:
        return self._max_pages_val


class ConcreteSourcing(BaseSourcing):
    def __init__(self, http_client: BaseHttpClient):
        self._http = http_client
        agent_tag = f"{self.SOURCE_NAME.lower().replace(' ', '-')}-sourcing"
        self.logger = get_logger(agent_tag)

    def source_detail(self, url: str) -> JobDetailUpdate:
        raw = self._http.fetch(url)
        if not raw:
            return JobDetailUpdate(url=url, job_details="")

        html_str = raw.decode("utf-8", errors="ignore")
        return self._parse_detail_page(html_str, url)
