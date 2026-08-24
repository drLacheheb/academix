import pytest
from core.infrastructure.services.lang_detector import LanguageDetector


@pytest.fixture(scope="module")
def detector() -> LanguageDetector:
    return LanguageDetector()


def test_detect_english_sentences(detector: LanguageDetector):
    text = (
        "We are seeking a Postdoctoral Researcher in Quantum Computing "
        "to join our research laboratory."
    )
    assert detector.detect_lang(text) == "en"


def test_detect_french_sentences(detector: LanguageDetector):
    text = (
        "Ce projet de doctorat vise à explorer la conversion optique non linéaire "
        "dans des dispositifs quantiques."
    )
    assert detector.detect_lang(text) == "fr"


def test_detect_german_sentences(detector: LanguageDetector):
    text = (
        "Wir suchen eine wissenschaftliche Mitarbeiterin oder einen wissenschaftlichen "
        "Mitarbeiter für das Institut für Physik."
    )
    assert detector.detect_lang(text) == "de"


def test_detect_dutch_sentences(detector: LanguageDetector):
    text = (
        "Als promovendus voer je zelfstandig wetenschappelijk onderzoek uit "
        "binnen het Instituut voor Informatica."
    )
    assert detector.detect_lang(text) == "nl"


def test_detect_empty_or_too_short(detector: LanguageDetector):
    assert detector.detect_lang("") == "en"
    assert detector.detect_lang("   ") == "en"
    assert detector.detect_lang("PhD") == "en"


def test_detect_ambiguous_short_phrases_defaults_to_english(detector: LanguageDetector):
    assert detector.detect_lang("Job Description") == "en"
    assert detector.detect_lang("Requirements") == "en"
    assert detector.detect_lang("Job Title") == "en"
