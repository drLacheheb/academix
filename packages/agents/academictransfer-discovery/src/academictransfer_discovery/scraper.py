import xml.etree.ElementTree as ET

from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class AcademicTransferDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "AcademicTransfer"
    SITEMAP_URL = "https://www.academictransfer.com/sitemap-vacancies.xml"

    def fetch_all_jobs_from_sitemap(self) -> list[Job]:
        raw = self._http.fetch(self.SITEMAP_URL)
        if not raw:
            self.logger.error("Failed to fetch AcademicTransfer vacancies sitemap")
            return []

        try:
            root = ET.fromstring(raw)
            jobs: list[Job] = []
            seen_urls: set[str] = set()

            # Standard XML sitemap namespace
            for url_elem in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                loc_elem = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc_elem is not None and loc_elem.text:
                    url = loc_elem.text.strip()
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        title_part = url.rstrip("/").split("/")[-1]
                        title = (
                            title_part.replace("-", " ").title()
                            if title_part
                            else "Academic Position"
                        )
                        jobs.append(Job(title=title, url=url, source=self.SOURCE_NAME))

            self.logger.info(f"Sitemap XML parsed successfully: found {len(jobs)} active job URLs")
            return jobs
        except Exception as e:
            self.logger.error(f"Error parsing AcademicTransfer sitemap XML: {e}")
            return []

    def _build_browse_url(self, page: int) -> str:
        return f"https://www.academictransfer.com/en/jobs/?page={page}&order=published"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        seen_urls: set[str] = set()
        for article in soup.find_all("article"):
            a = article.find("a", href=True)
            if a:
                href = str(a["href"])
                if href.startswith("/en/jobs/") and len(href) > len("/en/jobs/"):
                    h3 = article.find("h3")
                    if h3:
                        title = h3.get_text(strip=True)
                        link = "https://www.academictransfer.com" + href
                        if link not in seen_urls:
                            seen_urls.add(link)
                            jobs.append(Job(title=title, url=link, source=self.SOURCE_NAME))

        self.logger.info(f"  -> Found {len(jobs)} listings")
        return jobs
