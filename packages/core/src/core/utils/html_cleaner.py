import copy
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

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
    "dl",
    "div",
    "pre",
}


def normalize_markdown_separators(text: str) -> str:
    # 0. Normalize line endings and strip trailing whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # 1. Normalize unicode bullet characters at start of lines to standard '- '
    text = re.sub(r"^[ \t]*[•▪▫⁃‣∙·][ \t]*", "- ", text, flags=re.MULTILINE)
    # Normalize en/em dashes at start of line followed by whitespace:
    text = re.sub(r"^[ \t]*[–—][ \t]+", "- ", text, flags=re.MULTILINE)
    # Normalize hyphens attached to words at start of line (e.g. -Master -> - Master)
    text = re.sub(r"^[ \t]*-[ \t]*([^\s\-=*])", r"- \1", text, flags=re.MULTILINE)

    # 2. Normalize repeated separator characters (-, _, =, *, ~) to standard ---
    text = re.sub(r"^[ \t]*[-_=*~]{3,}[ \t]*$", "---", text, flags=re.MULTILINE)
    # 3. Collapse consecutive divider lines (including blank lines between them) into a single ---
    text = re.sub(r"(?:^[ \t]*---[ \t]*(?:\r?\n|$)\s*){2,}", "---\n\n", text, flags=re.MULTILINE)

    # 4. Strip redundant bold inside links: [**text**](url) -> [text](url)
    text = re.sub(r"\[\*\*([^\*\n]+?)\*\*\]\(", r"[\1](", text)

    # 5. Merge directly adjacent bold tags: **A****B** -> **AB**
    text = re.sub(r"\*{4,}", "", text)
    text = re.sub(r"\*\*[ \t]*\*\*", "", text)

    # 6. Fix missing space around markdown links
    text = re.sub(r"(\]\([^\)]+\))([a-zA-Z0-9])", r"\1 \2", text)
    text = re.sub(r"([a-zA-Z0-9])(\[[^\]]+\]\([^\)]+\))", r"\1 \2", text)

    # 7. Normalize comma spacing (excluding numbers like 1,000)
    text = re.sub(r"(?<!\d)[ \t]*,[ \t]*|[ \t]*,[ \t]*(?!\d)", ", ", text)

    # 8. Fix awkward punctuation spacing inside bold/italic
    text = re.sub(r"\*\*([^\*]+?)[ \t]+([,.;:：])\*\*", r"**\1**\2", text)
    text = re.sub(r"\*([^\*]+?)[ \t]+([,.;:：])\*", r"*\1*\2", text)

    # 9. Ensure blank line before bold headings: \n**Title**\n -> \n\n**Title**\n
    text = re.sub(r"([^\n])\n(\*\*[A-Z][^\n\*]+\*\*)\n", r"\1\n\n\2\n", text)

    # 10. Collapse empty lines between consecutive list items of the same type
    list_patterns = [
        r"[-*][ \t]+",  # Bullets (- or *)
        r"\d+\.[ \t]+",  # Numbered dot (1. 2.)
        r"\d+\)[ \t]+",  # Numbered paren (1) 2))
        r"[a-zA-Z][\.\)][ \t]+",  # Alphabetical (a. b. or a) b))
        r"\([a-zA-Z0-9]+\)[ \t]+",  # Parenthesized ((1) (2) or (a) (b))
    ]
    for lp in list_patterns:
        text = re.sub(
            rf"(^[ \t]*{lp}[^\n]+)\n+(?=[ \t]*{lp})",
            r"\1\n",
            text,
            flags=re.MULTILINE,
        )
    # 11. Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def inline_to_markdown(node: PageElement) -> str:
    if isinstance(node, NavigableString):
        return (
            str(node)
            .replace("\u200d", "")
            .replace("\u200b", "")
            .replace("\ufeff", "")
            .replace("\xa0", " ")
        )

    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()
    if tag_name == "br":
        return "\n"
    if tag_name in ["script", "style", "svg", "button", "iframe", "form", "noscript"]:
        return ""

    inner_text = "".join(inline_to_markdown(c) for c in node.children)

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
        raw_href = node.get("href")
        href = str(raw_href).strip() if raw_href is not None else ""
        s = inner_text.strip()
        if not s:
            return ""
        if href and not href.startswith("javascript"):
            prefix = " " if inner_text.startswith(" ") else ""
            suffix = " " if inner_text.endswith(" ") else ""
            return f"{prefix}[{s}]({href}){suffix}"
        return inner_text
    elif tag_name == "code":
        s = inner_text.strip()
        return f"`{s}`" if s else ""
    elif tag_name in ["u", "span", "label"]:
        return inner_text
    else:
        return inner_text


def parse_dl_to_dict(dl_tag: Tag) -> dict[str, str]:
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
                    val = inline_to_markdown(dd).strip()
            if key and val:
                data[key] = val
    return data


def html_to_markdown(node_or_html: Tag | str, heading_offset: int = 1) -> str:
    if isinstance(node_or_html, str):
        soup = BeautifulSoup(node_or_html, "html.parser")
        node = soup
    else:
        node = copy.copy(node_or_html)

    for bad in node.find_all(["script", "style", "svg", "button", "iframe", "form", "noscript"]):
        bad.decompose()

    lines: list[str] = []

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
                lines.append(t)
        elif isinstance(child, Tag):
            c_name = child.name.lower()
            if c_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                lvl = int(c_name[1]) + heading_offset
                htext = inline_to_markdown(child).strip()
                if htext:
                    lines.append(f"\n{'#' * lvl} {htext}\n")
            elif c_name in ["ul", "ol"]:
                for li in child.find_all("li", recursive=False):
                    litext = inline_to_markdown(li).strip()
                    if litext:
                        lines.append(f"- {litext}")
                lines.append("")
            elif c_name == "dl":
                d = parse_dl_to_dict(child)
                for k, v in d.items():
                    lines.append(f"- **{k}:** {v}")
                lines.append("")
            elif c_name == "table":
                rows = child.find_all("tr")
                for r in rows:
                    cols = [inline_to_markdown(c).strip() for c in r.find_all(["td", "th"])]
                    if cols:
                        lines.append("| " + " | ".join(cols) + " |")
                lines.append("")
            elif c_name in ["p", "div", "section", "article", "blockquote"]:
                if child.find(lambda t: t.name.lower() in BLOCK_TAGS and t is not child):
                    sub = html_to_markdown(child, heading_offset=heading_offset)
                    if sub:
                        lines.append(sub)
                else:
                    p_text = inline_to_markdown(child).strip()
                    if p_text:
                        lines.append(f"{p_text}\n")
            elif c_name == "a":
                raw_href = child.get("href")
                href = str(raw_href).strip() if raw_href is not None else ""
                text = inline_to_markdown(child).strip() or href
                if href and not href.startswith("javascript"):
                    lines.append(f"[{text}]({href})")

    result = "\n".join(line for line in lines if line)
    return normalize_markdown_separators(result)
