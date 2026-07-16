import json
import re

from core.models.job import Job
from core.scrapers.base import BaseSourcing, clean_html, extract_requirements_from_text


class AcademicTransferSourcing(BaseSourcing):
    SOURCE_NAME = "AcademicTransfer"

    def _parse_detail_page(self, html_content: str, job: Job) -> Job:
        h2_matches = list(
            re.finditer(r"<h2[^>]*>(.*?)</h2>", html_content, re.DOTALL | re.IGNORECASE)
        )
        sections: dict[str, str] = {}
        for idx, m in enumerate(h2_matches):
            heading = re.sub(r"<!--.*?-->", "", m.group(1)).strip().lower()
            next_pos = (
                h2_matches[idx + 1].start()
                if idx + 1 < len(h2_matches)
                else len(html_content)
            )
            sections[heading] = clean_html(html_content[m.end() : next_pos])

        def find_section(keywords: list[str]) -> str | None:
            for heading, content in sections.items():
                if any(kw in heading for kw in keywords):
                    return content
            return None

        job.description = find_section(
            [
                "job description",
                "description",
                "functieomschrijving",
                "omschrijving",
            ]
        )
        job.requirements = find_section(
            [
                "requirements",
                "functie-eisen",
                "eisen",
                "wat je meebrengt",
                "wat we verwachten",
                "what you bring",
            ]
        )

        json_ld_blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            html_content,
            re.DOTALL,
        )
        for block in json_ld_blocks:
            try:
                data = json.loads(block.strip())
                posting = None
                if data.get("@type") == "JobPosting":
                    posting = data
                elif data.get("mainEntity", {}).get("@type") == "JobPosting":
                    posting = data["mainEntity"]

                if posting:
                    deadline = posting.get("validThrough")
                    if deadline:
                        job.deadline = deadline.split("T")[0]

                    org = posting.get("hiringOrganization")
                    if org:
                        job.employer = org.get("name")

                    loc = posting.get("jobLocation", {})
                    addr = loc.get("address", {})
                    if addr:
                        city = addr.get("addressLocality")
                        country = addr.get("addressCountry")
                        if isinstance(country, dict):
                            country = country.get("name")
                        if city and country:
                            job.location = f"{city}, {country}"
                        elif country:
                            job.location = country
                        elif city:
                            job.location = city

                    if not job.description:
                        desc = posting.get("description")
                        if desc:
                            job.description = clean_html(desc)
                    break
            except Exception:
                continue

        if not job.requirements and job.description:
            job.requirements = extract_requirements_from_text(job.description)

        return job
