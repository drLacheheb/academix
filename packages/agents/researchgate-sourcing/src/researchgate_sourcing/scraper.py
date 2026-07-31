import json
import re
from datetime import datetime

from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import (
    ConcreteSourcing,
    clean_html,
    extract_requirements_from_text,
)


class ResearchGateSourcing(ConcreteSourcing):
    SOURCE_NAME = "ResearchGate"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        description: str | None = None
        employer: str | None = None
        location: str | None = None
        deadline: str | None = None

        # 1. Extract JSON-LD script with @type == "JobPosting"
        ld_scripts = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_content,
            re.DOTALL | re.I,
        )

        for script in ld_scripts:
            if "JobPosting" in script:
                try:
                    data = json.loads(script.strip())
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        # Description
                        raw_desc = data.get("description")
                        if raw_desc:
                            description = clean_html(raw_desc)

                        # Employer
                        org = data.get("hiringOrganization")
                        if isinstance(org, dict):
                            employer = org.get("name")
                        elif isinstance(org, str):
                            employer = org

                        # Location
                        loc_data = data.get("jobLocation")
                        if isinstance(loc_data, list) and loc_data:
                            loc_data = loc_data[0]
                        if isinstance(loc_data, dict):
                            addr = loc_data.get("address")
                            if isinstance(addr, dict):
                                city = addr.get("addressLocality")
                                state = addr.get("addressRegion")
                                country = addr.get("addressCountry")
                                parts = [p for p in [city, state, country] if p]
                                if parts:
                                    location = ", ".join(parts)

                        # Deadline
                        valid_through = data.get("validThrough")
                        if valid_through:
                            deadline = self._format_date(valid_through)

                        break
                except Exception as e:
                    self.logger.warning(f"Error parsing JSON-LD script for {url}: {e}")

        # 2. DOM fallbacks if fields missing
        if not description:
            main_block = soup.find(class_=re.compile(r"description|content|job-details", re.I))
            if main_block:
                description = clean_html(main_block.get_text(separator="\n", strip=True))
            else:
                description = clean_html(soup.get_text(separator="\n", strip=True))

        if not employer:
            emp_elem = soup.find(class_=re.compile(r"employer|company|organisation", re.I))
            if emp_elem:
                employer = clean_html(emp_elem.get_text(strip=True))

        if not location:
            loc_elem = soup.find(class_=re.compile(r"location|address", re.I))
            if loc_elem:
                location = clean_html(loc_elem.get_text(strip=True))

        # 3. Requirements extraction
        requirements = extract_requirements_from_text(description) if description else None

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

        # Try parsing ISO timestamp format "2026-09-13T..."
        if "T" in date_str:
            date_str = date_str.split("T")[0]

        # Try standard YYYY-MM-DD
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try RG format e.g. "13 Sep 2026" or "Sep 13, 2026"
        for fmt in ("%d %b %Y", "%b %d, %Y", "%d %B %Y", "%B %d, %Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str[:10] if len(date_str) >= 10 else None
