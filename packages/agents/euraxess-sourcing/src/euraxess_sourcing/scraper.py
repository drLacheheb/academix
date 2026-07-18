from bs4 import BeautifulSoup
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import clean_html, extract_requirements_from_text, ConcreteSourcing


class EuraxessSourcing(ConcreteSourcing):
    SOURCE_NAME = "EURAXESS"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Map all definition list elements
        metadata = {}
        for dt in soup.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = dt.get_text(strip=True).lower()
                metadata[key] = dd

        # Extract Application Deadline
        deadline = None
        deadline_dd = metadata.get("application deadline")
        if deadline_dd:
            time_tag = deadline_dd.find("time")
            if time_tag and time_tag.get("datetime"):
                deadline = time_tag["datetime"].split("T")[0]
            else:
                deadline = clean_html(deadline_dd.get_text(strip=True))

        # Extract Organisation/Company
        employer = None
        employer_dd = metadata.get("organisation/company") or metadata.get("company/institute")
        if employer_dd:
            employer = clean_html(employer_dd.get_text(strip=True))

        # Extract Country and City
        country_dd = metadata.get("country")
        city_dd = metadata.get("city")

        country = clean_html(country_dd.get_text(strip=True)) if country_dd else None
        city = clean_html(city_dd.get_text(strip=True)) if city_dd else None

        location = None
        if city and country:
            location = f"{city}, {country}"
        elif country:
            location = country
        elif city:
            location = city

        # 2. Extract sections dynamically using H2 headers siblings
        def extract_section(start_id: str, end_ids: list[str]) -> str | None:
            h2_start = soup.find("h2", id=start_id)
            if not h2_start:
                return None
            sibling_content = []
            for sibling in h2_start.next_siblings:
                if sibling.name == "h2" and sibling.get("id") in end_ids:
                    break
                if sibling.name:
                    sibling_content.append(sibling.get_text(strip=True))
                elif isinstance(sibling, str):
                    text = sibling.strip()
                    if text:
                        sibling_content.append(text)
            return clean_html(" ".join(sibling_content))

        description = extract_section(
            "offer-description",
            [
                "where-to-apply",
                "requirements",
                "additional-information",
                "work-locations",
            ],
        )
        requirements = extract_section(
            "requirements", ["additional-information", "work-locations", "contact"]
        )

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
