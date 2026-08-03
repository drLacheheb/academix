import os

import pymupdf4llm
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-pdf-parser")


def parse_pdf_to_markdown(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info(f"Parsing PDF: {file_path} using PyMuPDF4LLM")

    try:
        markdown_text = pymupdf4llm.to_markdown(file_path)
        logger.info(
            f"Successfully converted PDF {file_path} to Markdown ({len(markdown_text)} chars)"
        )
        return markdown_text
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
