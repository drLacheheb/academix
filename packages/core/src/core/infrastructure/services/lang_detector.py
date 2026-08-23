from core.domain.interfaces.services import BaseLanguageDetector
from lingua import Language, LanguageDetectorBuilder


class LanguageDetector(BaseLanguageDetector):
    LANGUAGE_MAP: dict[Language, str] = {
        Language.ENGLISH: "en",
        Language.FRENCH: "fr",
        Language.GERMAN: "de",
        Language.DUTCH: "nl",
        Language.SWEDISH: "sv",
        Language.SPANISH: "es",
        Language.ITALIAN: "it",
        Language.POLISH: "pl",
        Language.PORTUGUESE: "pt",
        Language.CHINESE: "zh",
        Language.JAPANESE: "ja",
    }

    def __init__(self) -> None:
        languages = list(self.LANGUAGE_MAP.keys())
        self._detector = (
            LanguageDetectorBuilder.from_languages(*languages)
            .with_minimum_relative_distance(0.1)
            .build()
        )

    def detect_lang(self, text: str) -> str:
        if not text or len(text.strip()) < 4:
            return "en"

        sample = text[:500]
        detected = self._detector.detect_language_of(sample)
        if detected is None:
            return "en"

        return self.LANGUAGE_MAP.get(detected, "en")
