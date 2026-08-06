import os
import re

import pymupdf4llm
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-pdf-parser")


def markdown_to_clean_text(md_text: str) -> str:
    if not md_text:
        return ""
    try:
        import html

        import inscriptis
        import markdown

        html_text = markdown.markdown(md_text)
        clean_text = inscriptis.get_text(html_text)
        clean_text = html.unescape(clean_text)
        clean_text = re.sub(r"\n{2,}", "\n", clean_text)
        return clean_text.strip()
    except Exception:
        clean_text = re.sub(r"\n{2,}", "\n", md_text)
        return clean_text.strip()


def parse_pdf_to_markdown(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info(f"Parsing PDF: {file_path} using PyMuPDF4LLM")

    try:
        raw_markdown = str(pymupdf4llm.to_markdown(file_path))
        clean_text = markdown_to_clean_text(raw_markdown)
        logger.info(
            f"Successfully converted PDF {file_path} via PyMuPDF4LLM to clean text"
            f" ({len(clean_text)} chars)"
        )
        return clean_text
    except Exception as e:
        logger.error(f"Failed to parse PDF via PyMuPDF4LLM: {e}")
        raise


def truncate_bibliography(text: str) -> str:
    lines = text.split("\n")
    truncated_lines = []

    # Common academic CV section headers for publications/references
    stop_headers = {
        "publications",
        "selected publications",
        "peer-reviewed publications",
        "bibliography",
        "references",
        "patents",
        "selected papers",
        "recent publications",
    }

    for line in lines:
        clean_line = line.strip().lower().replace("#", "").strip()
        # If we hit a header matching any stop keyword, truncate everything from here
        if clean_line in stop_headers:
            logger.info(f"Truncating PDF text at bibliography section header: '{line.strip()}'")
            break
        truncated_lines.append(line)

    return "\n".join(truncated_lines)
