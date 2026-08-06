import html
import re

from core.domain.interfaces.http import BaseHttpClient
from core.domain.interfaces.scrapers import BaseDiscovery, BaseSourcing
from core.domain.models.job import Job
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.logging.logger import get_logger


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    try:
        import inscriptis

        text = inscriptis.get_text(raw_html)
    except Exception:
        text = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<.*?>", "\n", text)
        text = re.sub(r"\n+", "\n", text)

    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_requirements_from_text(text: str) -> str | None:
    if not text:
        return None

    lines = text.split("\n")

    req_patterns = [
        r"\brequirements\b",
        r"\bwhat\s+you\s+bring\b",
        r"\bwhat\s+we\s+expect\b",
        r"\byour\s+profile\b",
        r"\bcandidate\s+profile\b",
        r"\bqualifications\b",
        r"\bwhat\s+you\s+need\b",
        r"\bwe\s+are\s+looking\s+for\b",
        r"\bwat\s+je\s+meebrengt\b",
        r"\bjouw\s+profiel\b",
        r"\bfunctie[- ]eisen\b",
        r"\bprofile\b",
        r"\bwhat\s+we\s+require\b",
        r"\brequirements\s+and\s+skills\b",
    ]
    req_keywords = [
        "requirements",
        "qualifications",
        "profile",
        "profil",
        "eisen",
        "bring",
        "meebrengt",
        "expect",
        "looking for",
        "expectations",
        "background",
        "criteria",
        "competenc",
        "skills",
        "experience",
    ]
    stop_patterns = [
        r"what we offer",
        r"what do we offer",
        r"what we offer you",
        r"we offer",
        r"wat we bieden",
        r"wat we jou bieden",
        r"wat bieden wij",
        r"arbeidsvoorwaarden",
        r"how to apply",
        r"application",
        r"apply",
        r"solliciteren",
        r"sollicitatie",
        r"about the university",
        r"about the group",
        r"^about\b",
        r"^over\s+",
        r"questions",
        r"inlichtingen",
        r"contact",
        r"information",
    ]

    req_index = -1
    for idx, line in enumerate(lines):
        clean_line = line.strip().lower()
        if len(clean_line) < 100:
            if any(re.search(pat, clean_line) for pat in req_patterns):
                req_index = idx
                break
            if any(
                re.search(r"\b" + re.escape(kw) + r"\b", clean_line) for kw in req_keywords
            ) and (
                "what" in clean_line
                or "you" in clean_line
                or "we" in clean_line
                or "jou" in clean_line
                or len(clean_line) < 30
            ):
                req_index = idx
                break

    if req_index == -1:
        return None

    extracted = []
    for line in lines[req_index + 1 :]:
        clean_line = line.strip().lower()
        if len(clean_line) < 100 and any(re.search(pat, clean_line) for pat in stop_patterns):
            break
        extracted.append(line)

    return "\n".join(extracted).strip() or None


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
            return JobDetailUpdate(url=url)

        html_str = raw.decode("utf-8", errors="ignore")
        return self._parse_detail_page(html_str, url)
