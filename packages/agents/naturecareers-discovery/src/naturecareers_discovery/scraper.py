import xml.etree.ElementTree as ET

from core.domain.models.job import Job
from core.infrastructure.scrapers.base import ConcreteDiscovery


class NatureCareersDiscovery(ConcreteDiscovery):
    SOURCE_NAME = "Nature Careers"
    SITEMAP_INDEX_URL = "https://www.nature.com/naturecareers/sitemapindex.xml"
    SITEMAP_JOBS_DEFAULT = "https://www.nature.com/naturecareers/sitemap2-1.xml"

    def fetch_all_jobs_from_sitemap(self) -> list[Job]:
        # 1. Inspect sitemap index for job sitemaps (e.g. sitemap2-1.xml)
        target_sitemaps: list[str] = [self.SITEMAP_JOBS_DEFAULT]
        index_raw = self._http.fetch(self.SITEMAP_INDEX_URL)
        if index_raw:
            try:
                xml_text = index_raw.decode("utf-8-sig", errors="ignore")
                root = ET.fromstring(xml_text)
                found_sitemaps = []
                for loc_elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                    if loc_elem is not None and loc_elem.text:
                        sm_url = loc_elem.text.strip()
                        if "sitemap2-" in sm_url:
                            found_sitemaps.append(sm_url)
                if found_sitemaps:
                    target_sitemaps = found_sitemaps
            except Exception as e:
                self.logger.warning(
                    f"Could not parse sitemap index XML, falling back to default: {e}"
                )

        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for sm_url in target_sitemaps:
            self.logger.info(f"Fetching Nature Careers job sitemap: {sm_url}")
            raw = self._http.fetch(sm_url)
            if not raw:
                self.logger.error(f"Failed to fetch sitemap: {sm_url}")
                continue

            try:
                xml_text = raw.decode("utf-8-sig", errors="ignore")
                root = ET.fromstring(xml_text)
                for loc_elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                    if loc_elem is not None and loc_elem.text:
                        url = loc_elem.text.strip()
                        if "/naturecareers/job/" in url and url not in seen_urls:
                            seen_urls.add(url)
                            title = self._extract_title_from_url(url)
                            jobs.append(Job(title=title, url=url, source=self.SOURCE_NAME))
            except Exception as e:
                self.logger.error(f"Error parsing sitemap XML ({sm_url}): {e}")

        self.logger.info(f"Parsed sitemap XML successfully: found {len(jobs)} active job URLs")
        return jobs

    def _extract_title_from_url(self, url: str) -> str:
        # URL pattern: .../naturecareers/job/<id>/<slug>/
        parts = url.rstrip("/").split("/")
        if len(parts) >= 1:
            slug = parts[-1]
            # If slug is numeric ID, check previous part
            if slug.isdigit() and len(parts) >= 2:
                slug = parts[-2]

            clean_title = slug.replace("-", " ").strip()
            if clean_title:
                return clean_title.title()

        return "Nature Careers Academic Position"

    def _build_browse_url(self, page: int) -> str:
        return f"https://www.nature.com/naturecareers/jobs?page={page}"

    def _parse_search_page(self, html_content: str) -> list[Job]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        jobs: list[Job] = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if "/naturecareers/job/" in href:
                full_url = href if href.startswith("http") else f"https://www.nature.com{href}"
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    title = a.get_text(strip=True) or self._extract_title_from_url(full_url)
                    jobs.append(Job(title=title, url=full_url, source=self.SOURCE_NAME))

        return jobs
