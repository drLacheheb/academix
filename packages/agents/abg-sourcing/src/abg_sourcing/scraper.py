import re
from datetime import datetime

from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import (
    ConcreteSourcing,
    clean_html,
    extract_requirements_from_text,
)


class AbgSourcing(ConcreteSourcing):
    SOURCE_NAME = "ABG"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")
        full_text = soup.get_text(separator="\n", strip=True)

        # 1. Employer
        employer = None
        company_link = soup.find("a", href=re.compile(r"http", re.I))
        if company_link:
            emp_text = clean_html(company_link.get_text(strip=True))
            if emp_text and not emp_text.startswith("http"):
                employer = emp_text

        # 2. Location
        location = None
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        if "Lieu de travail" in lines:
            idx = lines.index("Lieu de travail")
            if idx + 1 < len(lines):
                location = clean_html(lines[idx + 1])
        elif "Location" in lines:
            idx = lines.index("Location")
            if idx + 1 < len(lines):
                location = clean_html(lines[idx + 1])

        # 3. Deadline / Date
        deadline = None
        date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", full_text)
        if date_match:
            day, month, year = date_match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                deadline = dt.strftime("%Y-%m-%d")
            except ValueError:
                deadline = f"{year}-{month}-{day}"

        # 4. Description
        description = None
        content_div = soup.find("div", class_=re.compile(r"offre|content|detail", re.I))
        if content_div:
            description = clean_html(content_div.get_text(separator="\n", strip=True))
        else:
            description = clean_html(full_text)

        # 5. Requirements
        requirements = extract_requirements_from_text(description) if description else None

        return JobDetailUpdate(
            url=url,
            description=description,
            requirements=requirements,
            deadline=deadline,
            employer=employer,
            location=location,
        )
