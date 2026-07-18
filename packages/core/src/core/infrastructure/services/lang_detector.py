from core.domain.interfaces.services import BaseLanguageDetector


class LanguageDetector(BaseLanguageDetector):
    def detect_lang(self, text: str) -> str:
        """Returns ISO 639-1 code (e.g. 'en', 'nl', 'de')."""
        if not text or not text.strip():
            return "en"

        from fast_langdetect import detect

        try:
            result = detect(text)
            if isinstance(result, list) and len(result) > 0:
                return result[0]["lang"]
            elif isinstance(result, dict):
                return result["lang"]
            return "en"
        except Exception:
            return "en"
