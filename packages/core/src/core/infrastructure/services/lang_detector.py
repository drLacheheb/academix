from core.domain.interfaces.services import BaseLanguageDetector
from lingua import LanguageDetectorBuilder


class LanguageDetector(BaseLanguageDetector):
    def __init__(self) -> None:
        self._detector = (
            LanguageDetectorBuilder.from_all_spoken_languages()
            .with_minimum_relative_distance(0.1)
            .build()
        )

    def detect_lang(self, text: str) -> str:
        if not text or len(text.strip()) < 4:
            return "en"

        sample = text[:600]
        detected = self._detector.detect_language_of(sample)
        if detected is None or detected.iso_code_639_1 is None:
            return "en"

        return detected.iso_code_639_1.name.lower()
