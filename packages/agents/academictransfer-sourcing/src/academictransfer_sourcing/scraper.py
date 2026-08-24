import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing
from core.utils.html_cleaner import html_to_markdown, normalize_markdown_separators


class AcademicTransferSourcing(ConcreteSourcing):
    SOURCE_NAME = "AcademicTransfer"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract JSON-LD mainEntity
        job_posting: dict[str, Any] = {}
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text().strip(), strict=False)
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        job_posting = data
                        break
                    elif data.get("mainEntity", {}).get("@type") == "JobPosting":
                        job_posting = data["mainEntity"]
                        break
                    elif isinstance(data.get("@graph"), list):
                        for item in data["@graph"]:
                            if item.get("@type") == "JobPosting":
                                job_posting = item
                                break
            except Exception:
                continue

        # Title
        h1 = soup.find("h1")
        title = (
            job_posting.get("title")
            or (h1.get_text(strip=True) if h1 else None)
            or "Job Opportunity"
        )

        # Employer
        org = job_posting.get("hiringOrganization")
        employer = None
        if isinstance(org, dict):
            employer = org.get("name")
        elif isinstance(org, str):
            employer = org
        if not employer:
            emp_h3 = soup.find("h3", class_="text-lg")
            if emp_h3:
                employer = emp_h3.get_text(strip=True)
        employer = employer or "Unknown Employer"

        # Deadline
        deadline_val = job_posting.get("validThrough")
        deadline = "Not Specified"
        if deadline_val:
            deadline = str(deadline_val).split("T")[0]

        # Location
        loc = job_posting.get("jobLocation", {})
        location = "Not Specified"
        if isinstance(loc, dict):
            addr = loc.get("address", {})
            if isinstance(addr, dict):
                city = addr.get("addressLocality")
                country = addr.get("addressCountry")
                if isinstance(country, dict):
                    country = country.get("name")
                if city and country:
                    location = f"{city}, {country}"
                elif country:
                    location = str(country)
                elif city:
                    location = str(city)

        # Metadata fields
        work_hours = job_posting.get("workHours")
        employment_type = job_posting.get("employmentType")
        occupational_category = job_posting.get("occupationalCategory")

        edu_req = job_posting.get("educationRequirements")
        education = None
        if isinstance(edu_req, dict):
            education = edu_req.get("credentialCategory")
        elif isinstance(edu_req, str):
            education = edu_req

        salary_str = None
        base_sal = job_posting.get("baseSalary")
        if isinstance(base_sal, dict):
            val = base_sal.get("value", {})
            currency = base_sal.get("currency", "EUR")
            unit = val.get("unitText", "MONTH").lower() if isinstance(val, dict) else "month"
            if isinstance(val, dict):
                min_v = val.get("minValue")
                max_v = val.get("maxValue")
                if min_v and max_v:
                    salary_str = f"{currency} {min_v:,} - {max_v:,} per {unit}"
                elif min_v:
                    salary_str = f"{currency} {min_v:,} per {unit}"
                elif max_v:
                    salary_str = f"{currency} {max_v:,} per {unit}"

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
            f"- **Deadline:** {deadline}",
        ]
        if salary_str:
            doc.append(f"- **Salary:** {salary_str}")
        if work_hours:
            doc.append(f"- **Hours:** {work_hours}")
        if employment_type:
            doc.append(f"- **Contract Type:** {employment_type}")
        if education:
            doc.append(f"- **Education Level:** {education}")
        if occupational_category:
            doc.append(f"- **Discipline:** {occupational_category}")
        doc.append("")

        # 2. Extract Main Content Sections from HTML
        excluded_headers = re.compile(
            r"interessant voor jou|together @|nieuwsbrief|do's & don'ts|klaar voor je",
            re.I,
        )

        sections_found = False
        for sec in soup.find_all("section"):
            if sec.find("section"):
                continue

            h2 = sec.find("h2", recursive=False) or sec.find("h2")
            if not h2:
                continue

            h2_title = h2.get_text(strip=True)
            if not h2_title or excluded_headers.search(h2_title):
                continue

            content_div = sec.find("div", recursive=False) or sec.find("div")
            if content_div and isinstance(content_div, Tag):
                doc.append(f"## {h2_title}\n")
                doc.append(html_to_markdown(content_div))
                doc.append("")
                sections_found = True

        # Fallback to JSON-LD description if HTML sections were not matched
        if not sections_found and job_posting.get("description"):
            desc_soup = BeautifulSoup(str(job_posting["description"]), "html.parser")
            doc.append("## Description\n")
            doc.append(html_to_markdown(desc_soup))
            doc.append("")

        cleaned_text = normalize_markdown_separators("\n".join(doc))
        return JobDetailUpdate(url=url, job_details=cleaned_text)
