import re

from bs4 import BeautifulSoup
from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class ResearchGateDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "ResearchGate"
    BASE_URL = "https://www.researchgate.net"

    def _build_browse_url(self, page: int) -> str:
        return f"{self.BASE_URL}/jobs?page={page}"

    def _start_page(self) -> int:
        return 1

    def _parse_search_page(self, html_content: str) -> list[Job]:
        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        # Find links using regex matching /job/<ID>_<slug> pattern
        job_matches = re.findall(r'job/\d+_[^"\'\s<>?]+', html_content)
        for path in job_matches:
            full_url = f"{self.BASE_URL}/{path.lstrip('/')}"
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                title = self._extract_title(soup, path, full_url)
                jobs.append(Job(title=title, url=full_url, source=self.SOURCE_NAME))

        self.logger.info(f"  -> Found {len(jobs)} listings on page")
        return jobs

    def _extract_title(self, soup: BeautifulSoup, path: str, full_url: str) -> str:
        # Try finding corresponding <a> tag in HTML DOM
        a_elem = soup.find("a", href=re.compile(re.escape(path)))
        if a_elem:
            text = a_elem.get_text(strip=True)
            if text and text.lower() != "view" and len(text) > 3:
                return text

        # Fallback to slug title parsing: job/1038270_Physician_Head_of...
        parts = path.split("_", 1)
        if len(parts) > 1:
            slug = parts[1].replace("_", " ").replace("-", " ").strip()
            if slug:
                return slug.title()

        return "ResearchGate R&D Position"
