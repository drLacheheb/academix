import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing


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


def _block_to_markdown(node: Tag) -> str:
    out: list[str] = []

    for child in node.children:
        if isinstance(child, NavigableString):
            t = (
                str(child)
                .replace("\u200d", "")
                .replace("\u200b", "")
                .replace("\ufeff", "")
                .replace("\xa0", " ")
                .strip()
            )
            if t:
                out.append(t)
            continue

        if not isinstance(child, Tag):
            continue

        name = child.name.lower()
        if name in ["script", "style", "svg", "button", "iframe", "form"]:
            continue

        if name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            lvl = int(name[1])
            htext = child.get_text(strip=True)
            if htext and not any(
                b in htext.lower()
                for b in ["researchers also viewed", "discover more", "job description"]
            ):
                out.append(f"\n{'#' * lvl} {htext}\n")
        elif name in ["ul", "ol"]:
            for li in child.find_all("li", recursive=False):
                li_md = "".join(_inline_to_markdown(c) for c in li.children).strip()
                li_md = re.sub(r"[ \t]+", " ", li_md)
                if li_md:
                    out.append(f"- {li_md}")
            out.append("")
        elif name in ["p", "div", "section", "article"]:
            if child.find(
                ["p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote"]
            ):
                out.append(_block_to_markdown(child))
            else:
                p_md = "".join(_inline_to_markdown(c) for c in child.children).strip()
                p_md = re.sub(r"[ \t]+", " ", p_md)
                if p_md:
                    out.append(p_md)
                    out.append("")
        elif name == "blockquote":
            b_md = "".join(_inline_to_markdown(c) for c in child.children).strip()
            if b_md:
                out.append(f"> {b_md}\n")
        elif name == "table":
            for tr in child.find_all("tr"):
                cols = [c.get_text(separator=" ", strip=True) for c in tr.find_all(["td", "th"])]
                if cols:
                    out.append("| " + " | ".join(cols) + " |")
            out.append("")

    res = "\n".join(out)
    res = re.sub(r"\*{2,}\s*\*{2,}", "", res)
    res = re.sub(r"\*{4,}", "**", res)
    res = re.sub(r"\n{3,}", "\n\n", res).strip()
    return res


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
            desc_md = _block_to_markdown(desc_soup)
        else:
            desc_card = soup.find(
                class_=re.compile(r"job-detail-card__description|job-description", re.I)
            )
            desc_md = _block_to_markdown(desc_card or soup)

        if desc_md:
            doc.append("## Description\n")
            doc.append(desc_md)
            doc.append("")

        cleaned_text = "\n".join(doc)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return JobDetailUpdate(url=url, job_details=cleaned_text)
