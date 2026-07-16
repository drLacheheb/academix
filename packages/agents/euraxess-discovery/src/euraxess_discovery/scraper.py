import html
import re

from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class EuraxessDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "EURAXESS"

    def _build_browse_url(self, page: int) -> str:
        return f"https://euraxess.ec.europa.eu/jobs/search?sort%5Bname%5D=created&sort%5Bdirection%5D=DESC&page={page}"

    def _start_page(self) -> int:
        return 0

    def _parse_search_page(self, html_content: str) -> list[Job]:
        jobs: list[Job] = []
        matches = re.finditer(
            r'<a\s+href="(/jobs/\d+)"[^>]*>\s*<span>(.*?)</span>\s*</a>',
            html_content,
            re.DOTALL,
        )
        for m in matches:
            link = "https://euraxess.ec.europa.eu" + m.group(1)
            title = html.unescape(m.group(2).strip())
            jobs.append(
                Job(title=title, url=link, source=self.SOURCE_NAME)
            )

        print(f"  -> Found {len(jobs)} listings")
        return jobs

