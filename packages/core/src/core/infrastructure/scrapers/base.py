import html
import logging
import re

from core.domain.models.job import Job
from core.domain.models.schemas import JobDetailUpdate
from core.domain.interfaces.scrapers import BaseDiscovery, BaseSourcing
from core.domain.interfaces.http import BaseHttpClient


def clean_html(raw_html: str) -> str:
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<.*?>", "\n", text)
    text = re.sub(r"\n+", "\n", text)
    return html.unescape(text.strip())


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
                re.search(r"\b" + re.escape(kw) + r"\b", clean_line)
                for kw in req_keywords
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
        if len(clean_line) < 100 and any(
            re.search(pat, clean_line) for pat in stop_patterns
        ):
            break
        extracted.append(line)

    return "\n".join(extracted).strip() or None


class ConcreteDiscovery(BaseDiscovery):
    def __init__(self, http_client: BaseHttpClient, max_pages: int = 5):
        self._http = http_client
        self._max_pages_val = max_pages
        self.logger = logging.getLogger(f"agent.{self.SOURCE_NAME.lower().replace(' ', '-')}-discovery")

    def search_all(self, known_urls: set[str]) -> list[Job]:
        all_jobs: list[Job] = []
        page = self._start_page()
        max_pages = self._max_pages()

        self.logger.info(f"Starting broad search on {self.SOURCE_NAME} (sorting: newest first)...")

        while page < max_pages:
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

            new_jobs = [j for j in jobs_on_page if j.url not in known_urls]
            all_jobs.extend(new_jobs)

            seen_count = len(jobs_on_page) - len(new_jobs)
            self.logger.info(
                f"  -> Page {page}: Found {len(jobs_on_page)} listings ({len(new_jobs)} new, {seen_count} seen)"
            )

            if seen_count == len(jobs_on_page):
                self.logger.info(
                    f"  -> Page {page}: All jobs on this page have been seen. Stopping pagination."
                )
                break

            page += 1

        return all_jobs

    def _start_page(self) -> int:
        return 1

    def _max_pages(self) -> int:
        return self._max_pages_val


class ConcreteSourcing(BaseSourcing):
    def __init__(self, http_client: BaseHttpClient):
        self._http = http_client

    def source_detail(self, url: str) -> JobDetailUpdate:
        raw = self._http.fetch(url)
        if not raw:
            return JobDetailUpdate(url=url)

        html_str = raw.decode("utf-8", errors="ignore")
        return self._parse_detail_page(html_str, url)
