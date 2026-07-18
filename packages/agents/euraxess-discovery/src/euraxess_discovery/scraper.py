import re
from bs4 import BeautifulSoup
from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class EuraxessDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "EURAXESS"

    def _build_browse_url(self, page: int) -> str:
        return f"https://euraxess.ec.europa.eu/jobs/search?sort%5Bname%5D=created&sort%5Bdirection%5D=DESC&page={page}"

    def _start_page(self) -> int:
        return 0

    def _parse_search_page(self, html_content: str) -> list[Job]:
        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        for a in soup.find_all("a", href=re.compile(r"^/jobs/\d+$")):
            span = a.find("span")
            if span:
                title = span.get_text(strip=True)
                link = "https://euraxess.ec.europa.eu" + a["href"]
                jobs.append(
                    Job(title=title, url=link, source=self.SOURCE_NAME)
                )

        self.logger.info(f"  -> Found {len(jobs)} listings")
        return jobs
