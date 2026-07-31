import math
import os
import re

from bs4 import BeautifulSoup
from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class AbgDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "ABG"
    SEARCH_ENDPOINT = "https://www.abg.asso.fr/fr/candidatOffres/recherche"
    BASE_URL = "https://www.abg.asso.fr"

    HEADERS = {
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.abg.asso.fr",
        "Referer": "https://www.abg.asso.fr/fr/candidatOffres",
        "X-Prototype-Version": "1.7.3",
        "X-Requested-With": "XMLHttpRequest",
    }

    def _build_browse_url(self, page: int) -> str:
        return f"{self.SEARCH_ENDPOINT}?page={page}"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        return self._extract_jobs_from_html(html_content)

    def extract_total_count(self, html_content: str) -> int | None:
        # Match pattern like "451 offres" or "sur 451"
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text()
        match = re.search(r"(\d+)\s+offres?", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match_sur = re.search(r"sur\s+(\d+)", text, re.IGNORECASE)
        if match_sur:
            return int(match_sur.group(1))
        return None

    def _extract_jobs_from_html(self, html_content: str) -> list[Job]:
        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if "/candidatOffres/show/id_offre/" in href:
                title = a.get_text(strip=True)
                # Clean up title: if empty, check parent or sibling elements
                if not title or len(title) < 3:
                    parent = a.find_parent(["tr", "div", "li"])
                    if parent:
                        h3 = parent.find(["h3", "h2", "h4", "strong"])
                        if h3:
                            title = h3.get_text(strip=True)

                if not title:
                    title = "ABG Job Offer"

                full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    jobs.append(Job(title=title, url=full_url, source=self.SOURCE_NAME))

        return jobs

    def search_all(
        self,
        known_urls: set[str] | None = None,
        checkpoint_url: str | None = None,
        db_total_count: int | None = None,
    ) -> list[Job]:
        all_jobs: list[Job] = []
        seen_urls: set[str] = set()
        page = 1
        max_pages = self._max_pages()
        max_safety_pages = int(os.environ.get("MAX_SAFETY_PAGES", "500"))

        self.logger.info(
            f"Starting AJAX search on {self.SOURCE_NAME} (Delta-Bound + Checkpoint)..."
        )

        checkpoint_found = False
        lookback_pages_left: int | None = None

        while True:
            if max_pages > 0 and page > max_pages:
                self.logger.info(f"  -> Reached page limit ({max_pages} max pages). Stopping.")
                break

            if page > max_safety_pages:
                self.logger.warning(
                    f"Safety circuit breaker triggered: reached max depth of {max_safety_pages}."
                )
                break

            payload = (
                f"page={page}&orderBy=updated_at_desc&autoload=1"
                f"&criteria%5Bnb_offres_list%5D=50&reset_all=0"
            )

            raw = self._http.post(self.SEARCH_ENDPOINT, data=payload, headers=self.HEADERS)
            if not raw:
                self.logger.info(f"  -> Finished: POST request failed on page {page}.")
                break

            content = raw.decode("utf-8", errors="ignore")
            jobs_on_page = self._extract_jobs_from_html(content)

            if not jobs_on_page:
                self.logger.info(f"  -> Finished: No more listings found on page {page}.")
                break

            # Calculate Delta-Bound Max Pages on Page 1 if site total count is available
            if db_total_count is not None and page == 1:
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
