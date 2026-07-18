from bs4 import BeautifulSoup
from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class AcademicTransferDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "AcademicTransfer"

    def _build_browse_url(self, page: int) -> str:
        return f"https://www.academictransfer.com/en/jobs/?page={page}&order=published"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/en/jobs/") and len(href) > len("/en/jobs/"):
                h3 = a.find("h3")
                if h3:
                    title = h3.get_text(strip=True)
                    link = "https://www.academictransfer.com" + href
                    jobs.append(
                        Job(title=title, url=link, source=self.SOURCE_NAME)
                    )

        self.logger.info(f"  -> Found {len(jobs)} listings")
        return jobs
