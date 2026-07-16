import re

from core.models.job import Job
from core.scrapers.base import BaseSourcing, clean_html, extract_requirements_from_text


class EuraxessSourcing(BaseSourcing):
    SOURCE_NAME = "EURAXESS"

    def _parse_detail_page(self, html_content: str, job: Job) -> Job:
        deadline_match = re.search(
            r"<dt[^>]*>Application Deadline</dt>\s*<dd[^>]*>.*?<time\s+datetime=\"([^\"]+)\"",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if deadline_match:
            job.deadline = deadline_match.group(1).split("T")[0]
        else:
            fallback = re.search(
                r"<dt[^>]*>Application Deadline</dt>\s*<dd[^>]*>(.*?)</dd>",
                html_content,
                re.DOTALL | re.IGNORECASE,
            )
            if fallback:
                job.deadline = clean_html(fallback.group(1))

        employer_match = re.search(
            r"<dt[^>]*>Organisation/Company</dt>\s*<dd[^>]*>\s*<div>(.*?)</div>",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if not employer_match:
            employer_match = re.search(
                r"<dt[^>]*>Company/Institute</dt>\s*<dd[^>]*>(.*?)</dd>",
                html_content,
                re.DOTALL | re.IGNORECASE,
            )
        if employer_match:
            job.employer = clean_html(employer_match.group(1))

        country_match = re.search(
            r"<dt[^>]*>Country</dt>\s*<dd[^>]*>(.*?)</dd>",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        city_match = re.search(
            r"<dt[^>]*>City</dt>\s*<dd[^>]*>(.*?)</dd>",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )

        country = clean_html(country_match.group(1)) if country_match else None
        city = clean_html(city_match.group(1)) if city_match else None

        if city and country:
            job.location = f"{city}, {country}"
        elif country:
            job.location = country
        elif city:
            job.location = city

        def extract_section(start_id: str, end_ids: list[str]) -> str | None:
            start = re.search(
                r'<h2[^>]*id="' + re.escape(start_id) + r'"[^>]*>.*?</h2>',
                html_content,
                re.IGNORECASE | re.DOTALL,
            )
            if not start:
                return None
            start_pos = start.end()
            end_pos = len(html_content)
            for eid in end_ids:
                end = re.search(
                    r'<h2[^>]*id="' + re.escape(eid) + r'"[^>]*>',
                    html_content,
                    re.IGNORECASE | re.DOTALL,
                )
                if end:
                    end_pos = min(end_pos, end.start())
            return clean_html(html_content[start_pos:end_pos])

        job.description = extract_section(
            "offer-description",
            [
                "where-to-apply",
                "requirements",
                "additional-information",
                "work-locations",
            ],
        )
        job.requirements = extract_section(
            "requirements", ["additional-information", "work-locations", "contact"]
        )

        if not job.requirements and job.description:
            job.requirements = extract_requirements_from_text(job.description)

        return job
