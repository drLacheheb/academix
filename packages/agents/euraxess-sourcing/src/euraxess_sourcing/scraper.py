import copy
import re

from bs4 import BeautifulSoup, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing


def _parse_dl_to_dict(dl_tag: Tag) -> dict[str, str]:
    data: dict[str, str] = {}
    dts = dl_tag.find_all("dt")
    for dt in dts:
        dd = dt.find_next_sibling("dd")
        if dd:
            key = dt.get_text(strip=True)
            a_tag = dd.find("a")
            if a_tag and a_tag.get("href"):
                val = str(a_tag["href"]).strip()
            else:
                time_tag = dd.find("time")
                if time_tag and time_tag.get("datetime"):
                    val = str(time_tag["datetime"]).strip()
                else:
                    val = dd.get_text(strip=True)
            if key and val:
                data[key] = val
    return data


def _html_node_to_markdown(node: Tag) -> str:
    node_copy = copy.copy(node)
    for br in node_copy.find_all("br"):
        br.replace_with("\n")

    lines: list[str] = []
    for elem in node_copy.children:
        if isinstance(elem, str):
            text = elem.strip()
            if text:
                lines.append(text)
        elif isinstance(elem, Tag):
            tag_name = elem.name.lower()
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(tag_name[1]) + 1
                heading_text = elem.get_text(strip=True)
                if heading_text:
                    lines.append(f"\n{'#' * level} {heading_text}\n")
            elif tag_name in ["p", "div"]:
                if elem.find(["p", "ul", "ol", "h1", "h2", "h3", "h4", "dl"]):
                    lines.append(_html_node_to_markdown(elem))
                else:
                    p_text = elem.get_text(separator="\n", strip=True)
                    if p_text:
                        lines.append(f"{p_text}\n")
            elif tag_name in ["ul", "ol"]:
                for li in elem.find_all("li", recursive=False):
                    li_text = li.get_text(separator=" ", strip=True)
                    if li_text:
                        lines.append(f"- {li_text}")
                lines.append("")
            elif tag_name == "dl":
                d = _parse_dl_to_dict(elem)
                for k, v in d.items():
                    lines.append(f"- **{k}:** {v}")
                lines.append("")
            elif tag_name == "table":
                rows = elem.find_all("tr")
                for r in rows:
                    cols = [c.get_text(separator=" ", strip=True) for c in r.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")
                lines.append("")
            elif tag_name == "a":
                href = elem.get("href", "")
                text = elem.get_text(strip=True) or href
                if href:
                    lines.append(f"[{text}]({href})")
    return "\n".join(line for line in lines if line)


class EuraxessSourcing(ConcreteSourcing):
    SOURCE_NAME = "EURAXESS"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Job Title
        title_elem = soup.find("h1", class_="ecl-content-block__title") or soup.find(
            class_="ecl-content-block__title"
        )
        if not title_elem:
            h1s = soup.find_all("h1")
            title_candidates = [
                h.get_text(strip=True) for h in h1s if h.get_text(strip=True).lower() != "job offer"
            ]
            title = title_candidates[0] if title_candidates else "Job Opportunity"
        else:
            title = title_elem.get_text(strip=True)

        # 2. Extract Metadata from #job-information
        job_info_sec = soup.find("h2", id="job-information")
        job_info: dict[str, str] = {}
        if job_info_sec:
            parent = job_info_sec.find_parent("div") or job_info_sec.parent
            dl = parent.find("dl") if parent else None
            if dl:
                job_info = _parse_dl_to_dict(dl)

        # 3. Work Location(s)
        work_loc_sec = soup.find("h2", id="work-locations")
        work_loc_info: dict[str, str] = {}
        if work_loc_sec:
            parent = work_loc_sec.find_parent("div") or work_loc_sec.parent
            dl = parent.find("dl") if parent else None
            if dl:
                work_loc_info = _parse_dl_to_dict(dl)

        # 4. Where to apply
        apply_sec = soup.find("h2", id="where-to-apply")
        apply_info: dict[str, str] = {}
        if apply_sec:
            parent = apply_sec.find_parent("div") or apply_sec.parent
            dl = parent.find("dl") if parent else None
            if dl:
                apply_info = _parse_dl_to_dict(dl)

        employer = (
            job_info.get("Organisation/Company")
            or work_loc_info.get("Company/Institute")
            or "Unknown Employer"
        )

        country = job_info.get("Country") or work_loc_info.get("Country")
        city = work_loc_info.get("City")
        if city and country:
            location = f"{city}, {country}"
        elif country:
            location = country
        elif city:
            location = city
        else:
            location = "Not Specified"

        deadline_raw = job_info.get("Application Deadline")
        deadline = "Not Specified"
        if deadline_raw:
            if "T" in deadline_raw:
                deadline = deadline_raw.split("T")[0]
            else:
                deadline = deadline_raw

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
            f"- **Deadline:** {deadline}",
            "",
            "## Job Information",
        ]
        for k, v in job_info.items():
            doc.append(f"- **{k}:** {v}")
        doc.append("")

        # Offer Description
        desc_sec = soup.find("h2", id="offer-description")
        if desc_sec and isinstance(desc_sec, Tag):
            parent = desc_sec.find_parent("div") or desc_sec.parent
            if parent and isinstance(parent, Tag):
                desc_div = parent.find("div", class_="ecl") or desc_sec.find_next_sibling("div")
                if desc_div and isinstance(desc_div, Tag):
                    doc.append("## Offer Description\n")
                    doc.append(_html_node_to_markdown(desc_div))
                    doc.append("")

        # Requirements
        req_sec = soup.find("h2", id="requirements")
        if req_sec and isinstance(req_sec, Tag):
            parent = req_sec.find_parent("div") or req_sec.parent
            if parent and isinstance(parent, Tag):
                doc.append("## Requirements\n")
                for child in parent.find_all("div", recursive=False):
                    doc.append(_html_node_to_markdown(child))
                doc.append("")

        # Additional Information
        add_sec = soup.find("h2", id="additional-information")
        if add_sec and isinstance(add_sec, Tag):
            parent = add_sec.find_parent("div") or add_sec.parent
            if parent and isinstance(parent, Tag):
                doc.append("## Additional Information\n")
                for child in parent.find_all("div", recursive=False):
                    doc.append(_html_node_to_markdown(child))
                doc.append("")

        # Where to Apply
        if apply_info:
            doc.append("## Where to Apply\n")
            for k, v in apply_info.items():
                if v.startswith("http"):
                    doc.append(f"- **{k}:** [{v}]({v})")
                else:
                    doc.append(f"- **{k}:** {v}")
            doc.append("")

        # Work Locations
        if work_loc_info:
            doc.append("## Work Location(s)\n")
            for k, v in work_loc_info.items():
                doc.append(f"- **{k}:** {v}")
            doc.append("")

        cleaned_text = "\n".join(doc)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return JobDetailUpdate(url=url, job_details=cleaned_text)
