import copy
import re

from bs4 import BeautifulSoup, Tag
from core.domain.models.schemas import JobDetailUpdate
from core.infrastructure.scrapers.base import ConcreteSourcing


def _clean_esj_node(tag: Tag) -> str:
    node = copy.copy(tag)
    for br in node.find_all("br"):
        br.replace_with("\n")

    for bad in node.find_all(["script", "style", "svg", "button", "iframe", "form"]):
        bad.decompose()

    lines: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            t = child.strip()
            if t and not any(
                b in t.lower()
                for b in [
                    "job description start",
                    "job description end",
                    "share this job",
                    "don't forget to mention eurosciencejobs",
                ]
            ):
                lines.append(t)
        elif isinstance(child, Tag):
            c_name = child.name.lower()
            if c_name in ["h1", "h2", "h3", "h4", "h5"]:
                lvl = int(c_name[1]) + 1
                htext = child.get_text(strip=True)
                if htext and not any(
                    b in htext.lower()
                    for b in ["share this job", "more job searches", "never miss a job"]
                ):
                    lines.append(f"\n{'#' * lvl} {htext}\n")
            elif c_name in ["ul", "ol"]:
                for li in child.find_all("li", recursive=False):
                    litext = li.get_text(separator=" ", strip=True)
                    if litext:
                        lines.append(f"- {litext}")
                lines.append("")
            elif c_name in ["p", "div"]:
                if child.find(["p", "ul", "ol", "h1", "h2", "h3", "h4"]):
                    lines.append(_clean_esj_node(child))
                else:
                    ptext = child.get_text(separator="\n", strip=True)
                    if ptext and not any(
                        b in ptext.lower()
                        for b in [
                            "job description start",
                            "job description end",
                            "share this job",
                            "don't forget to mention eurosciencejobs",
                        ]
                    ):
                        lines.append(f"{ptext}\n")
            elif c_name == "a":
                href = str(child.get("href") or "").strip()
                text = str(child.get_text(strip=True) or href)
                if (
                    href
                    and not href.startswith("javascript")
                    and not any(b in text.lower() for b in ["share", "apply now"])
                ):
                    lines.append(f"[{text}]({href})")
    return "\n".join(line for line in lines if line)


class EuroScienceJobsSourcing(ConcreteSourcing):
    SOURCE_NAME = "EuroScienceJobs"

    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Main Column container
        col_main = (
            soup.find("div", class_="col-xl-9") or soup.find("div", class_="col-lg-8") or soup
        )

        # 2. Title, Employer, Location from H1 and H2 tags
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else None

        h2s = [h.get_text(strip=True) for h in col_main.find_all("h2") if h.get_text(strip=True)]

        if not title and h2s:
            title = h2s[0]
        title = title or "Job Opportunity"

        employer: str | None = None
        location: str | None = None
        if len(h2s) >= 2:
            employer = h2s[1]
        if len(h2s) >= 3:
            location = h2s[2]

        if not employer or not location:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                content_parts = str(og_title["content"]).split(" - ")
                if len(content_parts) >= 2 and not employer:
                    emp_loc = content_parts[1].split(", ")
                    employer = emp_loc[0].strip()
                    if len(emp_loc) > 1 and not location:
                        location = ", ".join(emp_loc[1:]).strip()

        employer = employer or "Unknown Employer"
        location = location or "Not Specified"

        # 3. Tags / Categories specifically under "More Job Searches"
        categories: list[str] = []
        more_searches_h = col_main.find(
            lambda tag: tag.name in ["h4", "h5"] and "More Job Searches" in tag.get_text()
        )
        if more_searches_h:
            parent_div = more_searches_h.find_parent("div", class_="row") or more_searches_h.parent
            if parent_div:
                for a in parent_div.find_all("a"):
                    if not a.find_parent("div", class_="sidebar"):
                        cat_text = a.get_text(strip=True)
                        if cat_text and cat_text.lower() != "more job searches":
                            categories.append(cat_text)

        # 4. Extract Job Description body
        rows = col_main.find_all("div", class_="row", recursive=False)
        job_row = rows[0] if rows else col_main

        job_row_copy = copy.copy(job_row)
        for h in job_row_copy.find_all("h2"):
            h.decompose()
        for bad in job_row_copy.find_all(["button", "form"]):
            bad.decompose()
        for bad_row in job_row_copy.find_all(
            lambda tag: tag.name in ["h4", "h5"] and "More Job Searches" in tag.get_text()
        ):
            p = bad_row.find_parent("div", class_="row")
            if p:
                p.decompose()
            else:
                bad_row.decompose()

        body_md = _clean_esj_node(job_row_copy)

        doc: list[str] = [
            f"# {title}",
            "",
            f"- **Employer:** {employer}",
            f"- **Location:** {location}",
        ]
        if categories:
            doc.append(f"- **Categories:** {', '.join(categories)}")
        doc.append("")

        if body_md:
            doc.append("## Job Description\n")
            doc.append(body_md)
            doc.append("")

        cleaned_text = "\n".join(doc)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
        return JobDetailUpdate(url=url, job_details=cleaned_text)
