from core.domain.interfaces.services import BaseLanguageDetector


class LanguageDetector(BaseLanguageDetector):
    def detect_lang(self, text: str) -> str:
        """Returns ISO 639-1 code (e.g. 'en', 'nl', 'de')."""
        if not text or not text.strip():
            return "en"

        from fast_langdetect import detect

        try:
            result = detect(text)
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                return str(result[0].get("lang", "en"))
            elif isinstance(result, dict):
                return str(result.get("lang", "en"))
            return "en"
        except Exception:
            return "en"
