import json
import re

from core.models.schemas import JobDetailUpdate
from core.scrapers.base import BaseSourcing, clean_html, extract_requirements_from_text


class AcademicTransferSourcing(BaseSourcing):
    SOURCE_NAME = "AcademicTransfer"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
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

        description = find_section(
            [
                "job description",
                "description",
                "functieomschrijving",
                "omschrijving",
            ]
        )
        requirements = find_section(
            [
                "requirements",
                "functie-eisen",
                "eisen",
                "wat je meebrengt",
                "wat we verwachten",
                "what you bring",
            ]
        )

        deadline = None
        employer = None
        location = None

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
                    dl = posting.get("validThrough")
                    if dl:
                        deadline = dl.split("T")[0]

                    org = posting.get("hiringOrganization")
                    if org:
                        employer = org.get("name")

                    loc = posting.get("jobLocation", {})
                    addr = loc.get("address", {})
                    if addr:
                        city = addr.get("addressLocality")
                        country = addr.get("addressCountry")
                        if isinstance(country, dict):
                            country = country.get("name")
                        if city and country:
                            location = f"{city}, {country}"
                        elif country:
                            location = country
                        elif city:
                            location = city

                    if not description:
                        desc = posting.get("description")
                        if desc:
                            description = clean_html(desc)
                    break
            except Exception:
                continue

        if not requirements and description:
            requirements = extract_requirements_from_text(description)

        return JobDetailUpdate(
            url=url,
            description=description,
            requirements=requirements,
            deadline=deadline,
            employer=employer,
            location=location,
        )
