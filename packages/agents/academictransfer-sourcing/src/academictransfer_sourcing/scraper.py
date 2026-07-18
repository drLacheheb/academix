import json
from bs4 import BeautifulSoup

from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import (
    clean_html,
    extract_requirements_from_text,
    ConcreteSourcing,
)


class AcademicTransferSourcing(ConcreteSourcing):
    SOURCE_NAME = "AcademicTransfer"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Parse headings and sections
        sections = {}
        for h2 in soup.find_all("h2"):
            heading = h2.get_text(strip=True).lower()
            sibling_content = []
            for sibling in h2.next_siblings:
                if sibling.name == "h2":
                    break
                if sibling.name:
                    sibling_content.append(sibling.get_text(strip=True))
                elif isinstance(sibling, str):
                    text = sibling.strip()
                    if text:
                        sibling_content.append(text)
            sections[heading] = clean_html(" ".join(sibling_content))

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

        # 2. Extract structured JSON-LD block
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text().strip(), strict=False)
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

        # 3. Extract sidebar metadata using p tag sibling matches
        metadata = []
        for field in [
            "Education level",
            "Weekly hours",
            "Research fields",
            "Job types",
        ]:
            p_label = soup.find(
                lambda tag: (
                    tag.name == "p"
                    and tag.get_text(strip=True).lower() == field.lower()
                )
            )
            if p_label:
                # Get next paragraph sibling
                p_val = p_label.find_next("p")
                if p_val:
                    val = p_val.get_text(strip=True)
                    metadata.append(f"{field}: {val}")

        if metadata:
            metadata_text = "\n".join(metadata)
            if requirements:
                requirements = requirements + "\n\n[Metadata]\n" + metadata_text
            else:
                requirements = "[Metadata]\n" + metadata_text

        return JobDetailUpdate(
            url=url,
            description=description,
            requirements=requirements,
            deadline=deadline,
            employer=employer,
            location=location,
        )
