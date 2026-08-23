import copy
import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing


def _clean_html_to_markdown(raw_html_or_tag: Tag | str) -> str:
    if isinstance(raw_html_or_tag, str):
        soup = BeautifulSoup(raw_html_or_tag, "html.parser")
        node = soup
    else:
        node = copy.copy(raw_html_or_tag)

    for br in node.find_all("br"):
        br.replace_with("\n")
    for bad in node.find_all(["script", "style", "svg", "button", "iframe", "form"]):
        bad.decompose()

    lines: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            t = child.strip()
            if t:
                lines.append(t)
        elif isinstance(child, Tag):
            c_name = child.name.lower()
            if c_name in ["h1", "h2", "h3", "h4", "h5"]:
                lvl = int(c_name[1]) + 1
                htext = child.get_text(strip=True)
                if htext:
                    lines.append(f"\n{'#' * lvl} {htext}\n")
            elif c_name in ["ul", "ol"]:
                for li in child.find_all("li", recursive=False):
                    litext = li.get_text(separator=" ", strip=True)
                    if litext:
                        lines.append(f"- {litext}")
                lines.append("")
            elif c_name in ["p", "div", "section"]:
                if child.find(["p", "ul", "ol", "h1", "h2", "h3", "h4", "table"]):
                    lines.append(_clean_html_to_markdown(child))
                else:
                    ptext = child.get_text(separator="\n", strip=True)
                    if ptext:
                        lines.append(f"{ptext}\n")
            elif c_name == "table":
                rows = child.find_all("tr")
                for r in rows:
                    cols = [c.get_text(separator=" ", strip=True) for c in r.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")
                lines.append("")
            elif c_name == "a":
                href = child.get("href", "")
                text = child.get_text(strip=True) or href
                if href:
                    lines.append(f"[{text}]({href})")
    return "\n".join(line for line in lines if line)


class NatureCareersSourcing(ConcreteSourcing):
    SOURCE_NAME = "Nature Careers"

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
            or (h1.get_text(strip=True) if h1 else None)
            or "Job Opportunity"
        )

        # Metadata from Definition Lists (<dl>)
        dl_meta: dict[str, str] = {}
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            for dt in dts:
                dd = dt.find_next_sibling("dd")
                if dd:
                    k = dt.get_text(strip=True)
                    if k.lower() == "website":
                        a = dd.find("a")
                        v = (
                            str(a["href"]).strip()
                            if (a and a.get("href"))
                            else dd.get_text(strip=True)
                        )
                    else:
                        raw_v = dd.get_text(separator=", ", strip=True)
                        v = re.sub(r"(\s*,\s*)+", ", ", raw_v).strip(", ")
                    if k and v:
                        dl_meta[k] = v

        # Resolve Employer
        employer = dl_meta.get("Employer")
        if not employer:
            org = job_posting.get("hiringOrganization")
            if isinstance(org, dict):
                employer = org.get("name")
            elif isinstance(org, str):
                employer = org
        employer = employer or "Unknown Employer"

        # Resolve Location
        location = dl_meta.get("Location")
        if not location:
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
        location = location or "Not Specified"

        # Resolve Deadline
        deadline = dl_meta.get("Closing date")
        if not deadline:
            vt = job_posting.get("validThrough")
            if vt:
                deadline = str(vt).split("T")[0]
        else:
            try:
                dt = datetime.strptime(deadline, "%d %b %Y")
                deadline = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        deadline = deadline or "Not Specified"

        salary = dl_meta.get("Salary")
        discipline = dl_meta.get("Discipline")
        job_type = dl_meta.get("Job Type")
        hours = dl_meta.get("Employment - Hours")
        duration = dl_meta.get("Duration")
        qualification = dl_meta.get("Qualification")
        sector = dl_meta.get("Sector")
        website = dl_meta.get("Website")

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
            f"- **Deadline:** {deadline}",
        ]
        if salary:
            doc.append(f"- **Salary:** {salary}")
        if hours:
            doc.append(f"- **Hours:** {hours}")
        if duration:
            doc.append(f"- **Duration:** {duration}")
        if job_type:
            doc.append(f"- **Job Type:** {job_type}")
        if qualification:
            doc.append(f"- **Qualification:** {qualification}")
        if discipline:
            doc.append(f"- **Discipline:** {discipline}")
        if sector:
            doc.append(f"- **Sector:** {sector}")
        if website:
            doc.append(f"- **Website:** [{website}]({website})")
        doc.append("")

        # 2. Main Job Description
        raw_desc = job_posting.get("description")
        if raw_desc:
            desc_md = _clean_html_to_markdown(str(raw_desc))
        else:
            panel = soup.find(
                "div", class_=re.compile(r"job-details|mds-tabs__panel__content", re.I)
            )
            desc_md = _clean_html_to_markdown(panel or soup)

        if desc_md:
            doc.append("## Description\n")
            doc.append(desc_md)
            doc.append("")

        cleaned_text = "\n".join(doc)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return JobDetailUpdate(url=url, job_details=cleaned_text)
