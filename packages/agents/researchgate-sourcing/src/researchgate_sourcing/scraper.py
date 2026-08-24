import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing
from core.utils.html_cleaner import html_to_markdown, normalize_markdown_separators


def _parse_rg_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    if "T" in date_str:
        date_str = date_str.split("T")[0]
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%d %B %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str[:10] if len(date_str) >= 10 else None


class ResearchGateSourcing(ConcreteSourcing):
    SOURCE_NAME = "ResearchGate"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. JSON-LD parsing
        job_posting: dict[str, Any] = {}
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text().strip(), strict=False)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    job_posting = data
                    break
            except Exception:
                continue

        # Title
        h1 = soup.find("h1")
        title = (
            job_posting.get("title")
            or (
                h1.get_text(strip=True)
                if (h1 and h1.get_text(strip=True) != "Research Jobs")
                else None
            )
            or "Job Opportunity"
        )

        # Employer
        org = job_posting.get("hiringOrganization")
        employer: str | None = None
        if isinstance(org, dict):
            employer = org.get("name")
        elif isinstance(org, str):
            employer = org
        if not employer:
            emp_div = soup.find(class_=re.compile(r"institution-name|company-name", re.I))
            if emp_div:
                employer = emp_div.get_text(strip=True)
        employer = employer or "Unknown Employer"

        # Location
        location: str | None = None
        loc_data = job_posting.get("jobLocation")
        if isinstance(loc_data, list) and loc_data:
            loc_data = loc_data[0]
        if isinstance(loc_data, dict):
            addr = loc_data.get("address", {})
            if isinstance(addr, dict):
                parts = [
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("addressCountry"),
                ]
                location = ", ".join(p for p in parts if p)
        if not location:
            loc_div = soup.find(class_=re.compile(r"location", re.I))
            if loc_div:
                location = loc_div.get_text(strip=True)
        location = location or "Not Specified"

        # Dates
        deadline = _parse_rg_date(job_posting.get("validThrough")) or "Not Specified"
        posted_date = _parse_rg_date(job_posting.get("datePosted"))

        # Research Areas
        research_areas: list[str] = []
        for card in soup.find_all(class_=re.compile(r"job-detail-card", re.I)):
            header = card.find(class_=re.compile(r"card__header", re.I))
            if header and "Areas of Research" in header.get_text():
                areas_text = (
                    card.get_text(separator=", ", strip=True)
                    .replace("Areas of Research, ", "")
                    .replace("Areas of Research", "")
                )
                for a in areas_text.split(","):
                    clean_a = a.strip()
                    if clean_a:
                        research_areas.append(clean_a)

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
            f"- **Deadline:** {deadline}",
        ]
        if posted_date:
            doc.append(f"- **Posted Date:** {posted_date}")
        if research_areas:
            doc.append(f"- **Research Areas:** {', '.join(research_areas)}")
        doc.append("")

        # 2. Description
        raw_desc = job_posting.get("description")
        if raw_desc:
            desc_soup = BeautifulSoup(str(raw_desc), "html.parser")
            desc_md = html_to_markdown(desc_soup)
        else:
            desc_card = soup.find(
                class_=re.compile(r"job-detail-card__description|job-description", re.I)
            )
            desc_md = html_to_markdown(desc_card or soup)

        if desc_md:
            doc.append("## Description\n")
            doc.append(desc_md)
            doc.append("")

        cleaned_text = normalize_markdown_separators("\n".join(doc))
        return JobDetailUpdate(url=url, job_details=cleaned_text)
