import re

from bs4 import BeautifulSoup
from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class EuroScienceJobsDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "EuroScienceJobs"
    BASE_URL = "https://www.eurosciencejobs.com"
    SITEMAP_URL = "https://www.eurosciencejobs.com/sitemap.xml"

    def fetch_all_jobs_from_sitemap(self) -> list[Job]:
        self.logger.info(f"Fetching EuroScienceJobs sitemap: {self.SITEMAP_URL}")
        raw = self._http.fetch(self.SITEMAP_URL)
        if not raw:
            self.logger.error("Failed to fetch EuroScienceJobs sitemap XML")
            return []

        xml_text = raw.decode("utf-8-sig", errors="ignore")
        locs = re.findall(r"<loc>(.*?)</loc>", xml_text)

        category_urls = [loc for loc in locs if "/jobs/" in loc or "/jobs_at/" in loc]

        self.logger.info(f"Discovered {len(category_urls)} category & employer sitemap URLs")

        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for cat_url in category_urls:
            cat_raw = self._http.fetch(cat_url)
            if not cat_raw:
                continue

            html = cat_raw.decode("utf-8", errors="ignore")
            matches = re.findall(r'/job_display/\d+/[^"\'\s<>?]+', html)

            for path in matches:
                full_url = (
                    path if path.startswith("http") else f"{self.BASE_URL}/{path.lstrip('/')}"
                )
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    title = self._extract_title_from_url(path)
                    jobs.append(Job(title=title, url=full_url, source=self.SOURCE_NAME))

        self.logger.info(
            f"Sitemap category crawl completed: found {len(jobs)} total unique active jobs"
        )
        return jobs

    def _extract_title_from_url(self, path: str) -> str:
        parts = path.rstrip("/").split("/")
        if len(parts) >= 1:
            slug = parts[-1]
            clean_title = slug.replace("_", " ").replace("-", " ").strip()
            if clean_title:
                return clean_title.title()
        return "EuroScienceJobs Academic Position"

    def _build_browse_url(self, page: int) -> str:
        return f"{self.BASE_URL}/job_search"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if "/job_display/" in href:
                full_url = (
                    href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                )
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    title = a.get_text(strip=True) or self._extract_title_from_url(full_url)
                    jobs.append(Job(title=title, url=full_url, source=self.SOURCE_NAME))

        return jobs
