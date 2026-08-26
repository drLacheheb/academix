import copy
import re

from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing
from core.utils.html_cleaner import html_to_markdown, normalize_markdown_separators


class EuroScienceJobsSourcing(ConcreteSourcing):
    SOURCE_NAME = "EuroScienceJobs"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Main Column container
        col_main = (
            soup.find("div", class_="col-xl-9") or soup.find("div", class_="col-lg-8") or soup
        )

        # 2. Title, Employer, Location from H1 and H2 tags
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else None

        h2s = [h.get_text(strip=True) for h in col_main.find_all("h2") if h.get_text(strip=True)]

        if not title and h2s:
            title = h2s[0]
        title = title or "Job Opportunity"

        employer: str | None = None
        location: str | None = None
        if len(h2s) >= 2:
            employer = h2s[1]
        if len(h2s) >= 3:
            location = h2s[2]

        if not employer or not location:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                content_parts = str(og_title["content"]).split(" - ")
                if len(content_parts) >= 2 and not employer:
                    emp_loc = content_parts[1].split(", ")
                    employer = emp_loc[0].strip()
                    if len(emp_loc) > 1 and not location:
                        location = ", ".join(emp_loc[1:]).strip()

        employer = employer or "Unknown Employer"
        location = location or "Not Specified"

        # 3. Tags / Categories specifically under "More Job Searches"
        categories: list[str] = []
        more_searches_h = col_main.find(
            lambda tag: tag.name in ["h4", "h5"] and "More Job Searches" in tag.get_text()
        )
        if more_searches_h:
            parent_div = more_searches_h.find_parent("div", class_="row") or more_searches_h.parent
            if parent_div:
                for a in parent_div.find_all("a"):
                    if not a.find_parent("div", class_="sidebar"):
                        cat_text = a.get_text(strip=True)
                        if cat_text and cat_text.lower() != "more job searches":
                            categories.append(cat_text)

        # 4. Extract Job Description body
        rows = col_main.find_all("div", class_="row", recursive=False)
        job_row = rows[0] if rows else col_main

        job_row_copy = copy.copy(job_row)
        for h in job_row_copy.find_all("h2"):
            h.decompose()
        for bad in job_row_copy.find_all(["button", "form"]):
            bad.decompose()
        for bad_row in job_row_copy.find_all(
            lambda tag: tag.name in ["h4", "h5"] and "More Job Searches" in tag.get_text()
        ):
            p = bad_row.find_parent("div", class_="row")
            if p:
                p.decompose()
            else:
                bad_row.decompose()

        unwanted_pattern = (
            r"job description (start|end)|share this job|"
            r"don't forget to mention eurosciencejobs"
        )
        for unwanted in job_row_copy.find_all(string=re.compile(unwanted_pattern, re.I)):
            unwanted.extract()

        body_md = html_to_markdown(job_row_copy)

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
        ]
        if categories:
            doc.append(f"- **Categories:** {', '.join(categories)}")
        doc.append("")

        if body_md:
            doc.append("## Job Description\n")
            doc.append(body_md)
            doc.append("")

        cleaned_text = normalize_markdown_separators("\n".join(doc))
        return JobDetailUpdate(url=url, job_details=cleaned_text)
