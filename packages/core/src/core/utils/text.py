import unicodedata


def strip_accents(text: str | None) -> str | None:
    if not text:
        return text
    if not isinstance(text, str):
        text = str(text)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("utf-8")
