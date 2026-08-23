import json
import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing

BLOCK_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "table",
    "blockquote",
    "hr",
    "section",
    "article",
}


def _inline_to_markdown(node: PageElement) -> str:
    if isinstance(node, NavigableString):
        text = (
            str(node)
            .replace("\u200d", "")
            .replace("\u200b", "")
            .replace("\ufeff", "")
            .replace("\xa0", " ")
        )
        return text

    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name == "br":
        return "\n"
    if tag_name in ["script", "style", "svg", "button", "iframe", "form"]:
        return ""

    inner_text = "".join(_inline_to_markdown(c) for c in node.children)

    if tag_name in ["strong", "b"]:
        s = inner_text.strip()
        if not s:
            return ""
        prefix = " " if inner_text.startswith(" ") else ""
        suffix = " " if inner_text.endswith(" ") else ""
        return f"{prefix}**{s}**{suffix}"
    elif tag_name in ["em", "i"]:
        s = inner_text.strip()
        if not s:
            return ""
        prefix = " " if inner_text.startswith(" ") else ""
        suffix = " " if inner_text.endswith(" ") else ""
        return f"{prefix}*{s}*{suffix}"
    elif tag_name == "a":
        href = str(node.get("href") or "").strip()
        s = inner_text.strip()
        if not s:
            return ""
        s = re.sub(r"^\[+|\]+$", "", s).strip()
        if href and not href.startswith("javascript"):
            return f"[{s}]({href})"
        return s
    elif tag_name in ["u", "span"]:
        return inner_text
    elif tag_name == "code":
        s = inner_text.strip()
        return f"`{s}`" if s else ""
    else:
        return inner_text


def _element_to_markdown(node: Tag) -> str:
    out: list[str] = []
    inline_buffer: list[PageElement] = []

    def flush_inline():
        nonlocal inline_buffer
        if inline_buffer:
            p_text = "".join(_inline_to_markdown(n) for n in inline_buffer).strip()
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in p_text.splitlines()]
            p_clean = "\n".join(line for line in lines if line)
            if p_clean:
                out.append(p_clean)
                out.append("")
            inline_buffer = []

    for child in node.children:
        if isinstance(child, NavigableString):
            inline_buffer.append(child)
            continue

        if not isinstance(child, Tag):
            continue

        name = child.name.lower()
        if name in ["script", "style", "svg", "button", "iframe", "form"]:
            continue

        if name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            flush_inline()
            lvl = int(name[1])
            htext = child.get_text(strip=True)
            if htext:
                out.append(f"\n{'#' * lvl} {htext}\n")
        elif name in ["ul", "ol"]:
            flush_inline()
            for li in child.find_all("li", recursive=False):
                li_md = "".join(_inline_to_markdown(c) for c in li.children).strip()
                li_md = re.sub(r"[ \t]+", " ", li_md)
                if li_md:
                    out.append(f"- {li_md}")
            out.append("")
        elif name == "blockquote":
            flush_inline()
            b_md = "".join(_inline_to_markdown(c) for c in child.children).strip()
            if b_md:
                out.append(f"> {b_md}\n")
        elif name == "table":
            flush_inline()
            for tr in child.find_all("tr"):
                cols = [c.get_text(separator=" ", strip=True) for c in tr.find_all(["td", "th"])]
                if cols:
                    out.append("| " + " | ".join(cols) + " |")
            out.append("")
        elif name in ["p", "div", "section", "article"]:
            if any(isinstance(c, Tag) and c.name.lower() in BLOCK_TAGS for c in child.children):
                flush_inline()
                out.append(_element_to_markdown(child))
            else:
                flush_inline()
                p_text = "".join(_inline_to_markdown(c) for c in child.children).strip()
                lines = [re.sub(r"[ \t]+", " ", line).strip() for line in p_text.splitlines()]
                p_clean = "\n".join(line for line in lines if line)
                if p_clean:
                    out.append(p_clean)
                    out.append("")
        else:
            inline_buffer.append(child)

    flush_inline()

    res = "\n".join(out)
    res = re.sub(r"\*{2,}\s*\*{2,}", "", res)
    res = re.sub(r"\*{4,}", "**", res)
    res = re.sub(r"\n{3,}", "\n\n", res).strip()
    return res


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
                doc.append(_element_to_markdown(content_div))
                doc.append("")
                sections_found = True

        # Fallback to JSON-LD description if HTML sections were not matched
        if not sections_found and job_posting.get("description"):
            desc_soup = BeautifulSoup(str(job_posting["description"]), "html.parser")
            doc.append("## Description\n")
            doc.append(_element_to_markdown(desc_soup))
            doc.append("")

        cleaned_text = "\n".join(doc)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return JobDetailUpdate(url=url, job_details=cleaned_text)
