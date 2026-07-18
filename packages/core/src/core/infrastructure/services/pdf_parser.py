import os
import logging
from io import BytesIO
import pypdfium2 as pdfium
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


_converter: DocumentConverter | None = None


def get_document_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        logger.info("Initializing global Docling DocumentConverter (happens once)")
        _converter = DocumentConverter()
    return _converter


def parse_pdf_to_markdown(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info(
        f"Rasterizing and parsing PDF: {file_path} using visual Docling pipeline"
    )

    converter = get_document_converter()

    try:
        markdown_pages = []
        with pdfium.PdfDocument(file_path) as pdf:
            for i in range(len(pdf)):
                page = pdf[i]
                # Render page to PIL Image at 2.0x scale for high resolution
                bitmap = page.render(scale=2.0)
                pil_img = bitmap.to_pil()

                # Save PIL image to byte buffer as PNG
                img_buffer = BytesIO()
                pil_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)

                # Wrap in DocumentStream
                source = DocumentStream(name=f"page_{i}.png", stream=img_buffer)

                # Convert page image
                result = converter.convert(source)
                markdown_pages.append(result.document.export_to_markdown())

                img_buffer.close()

        markdown_text = "\n\n".join(markdown_pages)
        logger.info(
            f"Successfully rasterized and converted PDF {file_path} to Markdown ({len(markdown_text)} chars)"
        )
        return markdown_text
    except Exception as e:
        logger.error(f"Failed to parse PDF via rasterization: {e}")
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
            logger.info(
                f"Truncating PDF text at bibliography section header: '{line.strip()}'"
            )
            break
        truncated_lines.append(line)

    return "\n".join(truncated_lines)
