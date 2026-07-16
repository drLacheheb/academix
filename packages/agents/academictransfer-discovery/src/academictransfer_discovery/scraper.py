import html
import re

from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class AcademicTransferDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "AcademicTransfer"

    def _build_browse_url(self, page: int) -> str:
        return f"https://www.academictransfer.com/en/jobs/?page={page}&order=published"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        jobs: list[Job] = []
        matches = re.finditer(
            r'<a href="(/en/jobs/[^"]+)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>',
            html_content,
            re.DOTALL,
        )
        for m in matches:
            link = "https://www.academictransfer.com" + m.group(1)
            title = html.unescape(m.group(2).strip())
            jobs.append(
                Job(title=title, url=link, source=self.SOURCE_NAME)
            )

        print(f"  -> Found {len(jobs)} listings")
        return jobs

