import copy
import re

from bs4 import BeautifulSoup, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing
from core.utils.html_cleaner import html_to_markdown, normalize_markdown_separators


class AbgSourcing(ConcreteSourcing):
    SOURCE_NAME = "ABG"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Job Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Job Opportunity"

        # 2. Metadata table (.tab_offre_infos)
        ref_id: str | None = None
        offer_type: str | None = None
        date_posted: str | None = None
        funding: str | None = None

        tab = soup.find("table", class_="tab_offre_infos")
        if tab:
            cells = [
                c.get_text(strip=True) for c in tab.find_all(["td", "th"]) if c.get_text(strip=True)
            ]
            for cell in cells:
                if "Réf" in cell or "ABG-" in cell:
                    ref_id = cell
                elif any(
                    t in cell.lower()
                    for t in [
                        "thèse",
                        "doctorat",
                        "post-doctorat",
                        "emploi",
                        "stage",
                        "cdd",
                        "cdi",
                    ]
                ):
                    offer_type = cell
                elif re.search(r"\d{2}/\d{2}/\d{4}", cell):
                    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", cell)
                    if m:
                        d, mth, y = m.groups()
                        date_posted = f"{y}-{mth}-{d}"
                elif "financement" in cell.lower():
                    funding = cell

        # 3. Scientific Domains (div.box before div.desc)
        domains: list[str] = []
        outer_offre = soup.find("div", class_="offrePage")
        if outer_offre:
            domain_box = outer_offre.find("div", class_="box")
            if domain_box and not domain_box.find("h2"):
                for li in domain_box.find_all("li"):
                    dt = li.get_text(strip=True)
                    if dt:
                        domains.append(dt)

        # 4. Iterate structured div.box inside div.desc
        desc_div = soup.find("div", class_="desc")
        sections: list[tuple[str, list[tuple[str | None, str]]]] = []

        if desc_div:
            for box in desc_div.find_all("div", class_="box", recursive=False):
                h2 = box.find("h2", recursive=False) or box.find("h2")
                if not h2:
                    continue
                h2_title = h2.get_text(strip=True)

                box_items: list[tuple[str | None, str]] = []

                for child in box.children:
                    if not isinstance(child, Tag) or child == h2:
                        continue
                    raw_cls = child.get("class")
                    cls_list = (
                        raw_cls
                        if isinstance(raw_cls, list)
                        else ([raw_cls] if isinstance(raw_cls, str) else [])
                    )
                    if "text" in cls_list:
                        txt = html_to_markdown(child)
                        if txt:
                            box_items.append((None, txt))
                    elif "item" in cls_list:
                        head_elem = child.find(["h3", "h4", "label", "strong"])
                        h3_title = (
                            head_elem.get_text(strip=True).rstrip(":")
                            if head_elem and isinstance(head_elem, Tag)
                            else None
                        )
                        item_text_div = child.find("div", class_="text")
                        if not item_text_div:
                            child_copy = copy.copy(child)
                            if head_elem:
                                h_in_copy = child_copy.find(["h3", "h4", "label", "strong"])
                                if h_in_copy and isinstance(h_in_copy, Tag):
                                    h_in_copy.decompose()
                            txt = html_to_markdown(child_copy)
                        else:
                            txt = html_to_markdown(item_text_div)
                        if txt:
                            box_items.append((h3_title, txt))
                    elif child.name in ["ul", "ol", "p", "div"]:
                        txt = html_to_markdown(child)
                        if txt:
                            box_items.append((None, txt))

                if box_items:
                    sections.append((h2_title, box_items))

        # 5. Resolve metadata fields from sections
        employer: str | None = None
        location: str | None = None
        start_date: str | None = None
        deadline: str | None = None

        for h2_title, items in sections:
            h2_lower = h2_title.lower()
            for h3_title, text in items:
                h3_lower = (h3_title or "").lower()
                if "établissement" in h2_lower or "labo" in h2_lower or "société" in h2_lower:
                    if not employer:
                        employer = text.splitlines()[0].strip()
                elif "pays" in h3_lower or "lieu" in h3_lower:
                    location = text.splitlines()[0].strip()
                elif "prise de fonction" in h3_lower or "date de début" in h3_lower:
                    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
                    if m:
                        d, mth, y = m.groups()
                        start_date = f"{y}-{mth}-{d}"
                    else:
                        start_date = text.splitlines()[0].strip()
                elif (
                    "date limite" in h3_lower
                    or "candidature" in h3_lower
                    or "profil du candidat" in h2_lower
                ):
                    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
                    if m and not deadline:
                        d, mth, y = m.groups()
                        deadline = f"{y}-{mth}-{d}"

        employer = employer or "Unknown Employer"
        location = location or "France"

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
        ]
        if deadline:
            doc.append(f"- **Deadline:** {deadline}")
        if date_posted:
            doc.append(f"- **Posted Date:** {date_posted}")
        if start_date:
            doc.append(f"- **Start Date:** {start_date}")
        if offer_type:
            doc.append(f"- **Contract / Type:** {offer_type}")
        if funding:
            doc.append(f"- **Funding:** {funding}")
        if domains:
            doc.append(f"- **Discipline:** {', '.join(domains)}")
        if ref_id:
            doc.append(f"- **Reference:** {ref_id}")
        doc.append("")

        for h2_title, items in sections:
            doc.append(f"## {h2_title}\n")
            for h3_title, text in items:
                if h3_title:
                    if "\n" not in text and len(text) < 100:
                        doc.append(f"- **{h3_title}:** {text}")
                    else:
                        doc.append(f"### {h3_title}\n\n{text}")
                else:
                    doc.append(text)
                doc.append("")
        cleaned_text = normalize_markdown_separators("\n".join(doc))
        return JobDetailUpdate(url=url, job_details=cleaned_text)
