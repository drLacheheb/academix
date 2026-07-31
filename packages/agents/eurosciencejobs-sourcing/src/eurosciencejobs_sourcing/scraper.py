import re
from datetime import datetime

from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import (
    ConcreteSourcing,
    clean_html,
    extract_requirements_from_text,
)


class EuroScienceJobsSourcing(ConcreteSourcing):
    SOURCE_NAME = "EuroScienceJobs"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Main Job Display Container
        job_display = soup.find(class_="jobDisplay") or soup.find(
            class_=re.compile(r"jobDisplay", re.I)
        )
        if job_display:
            raw_desc = job_display.get_text(separator="\n", strip=True)
        else:
            raw_desc = soup.get_text(separator="\n", strip=True)

        description = clean_html(raw_desc)

        # 2. Extract Requirements
        requirements = extract_requirements_from_text(description) if description else None

        # 3. Extract Metadata
        employer: str | None = None
        location: str | None = None
        deadline: str | None = None

        # Check date pattern inside description
        deadline_match = re.search(
            r"(?:deadline|expires|closing date|apply by):\s*([\d\w\s,/-]+)",
            description,
            re.IGNORECASE,
        )
        if deadline_match:
            deadline = self._format_date(deadline_match.group(1).strip())

        return JobDetailUpdate(
            url=url,
            description=description,
            requirements=requirements,
            deadline=deadline,
            employer=employer,
            location=location,
        )

    def _format_date(self, date_str: str) -> str | None:
        if not date_str:
            return None

        if "T" in date_str:
            date_str = date_str.split("T")[0]

        for fmt in ("%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d %B %Y", "%B %d, %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str[:10] if len(date_str) >= 10 else None
