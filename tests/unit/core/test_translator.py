import os

import pytest
from core.infrastructure.services.translator import (
    DATE_REGEX,
    DIVIDER_REGEX,
    PREFIX_REGEX,
    URL_REGEX,
    NllbTranslator,
    to_flores_code,
)

MODEL_PATH = os.path.abspath("models/mijuanlo/nllb-200-distilled-600M-ct2-int8")
MODEL_EXISTS = os.path.exists(os.path.join(MODEL_PATH, "model.bin"))


def test_to_flores_code_dynamic_resolution():
    assert to_flores_code("en") == "eng_Latn"
    assert to_flores_code("fr") == "fra_Latn"
    assert to_flores_code("de") == "deu_Latn"
    assert to_flores_code("nl") == "nld_Latn"
    assert to_flores_code("el") == "ell_Grek"
    assert to_flores_code("ar") == "ara_Arab"
    assert to_flores_code("zh") in ["zho_Hans", "cmn_Hans"]
    assert to_flores_code("") is None
    assert to_flores_code("   ") is None


def test_structure_preservation_regexes():
    assert DATE_REGEX.match("2026-08-31")
    assert DATE_REGEX.match("31/08/2026")
    assert DATE_REGEX.match("01.10.2025")
    assert not DATE_REGEX.match("Not a date")

    assert DIVIDER_REGEX.match("---")
    assert DIVIDER_REGEX.match("***")
    assert not DIVIDER_REGEX.match("--")

    assert URL_REGEX.match("https://www.abg.asso.fr/fr/candidatOffres/show/id_offre/133882")
    assert not URL_REGEX.match("Hello https://example.com")

    m_h1 = PREFIX_REGEX.match("# Main Heading")
    assert m_h1 and m_h1.group(1) == "# " and m_h1.group(2) == "Main Heading"

    m_h2 = PREFIX_REGEX.match("## Sub Heading")
    assert m_h2 and m_h2.group(1) == "## " and m_h2.group(2) == "Sub Heading"

    m_field = PREFIX_REGEX.match("- **Employer:** ESPCI Paris")
    assert m_field and m_field.group(1) == "- **Employer:** " and m_field.group(2) == "ESPCI Paris"


@pytest.fixture(scope="module")
def translator() -> NllbTranslator:
    if not MODEL_EXISTS:
        pytest.skip("NLLB model weights not available locally")
    return NllbTranslator(MODEL_PATH)


def test_pure_english_skips_translation(translator: NllbTranslator):
    text = (
        "# Quantum Physicist\n\n"
        "- **Employer:** University of Oxford\n"
        "- **Deadline:** 2026-08-31\n\n"
        "We are looking for an experienced researcher in quantum computing."
    )
    result_text, was_translated = translator.translate(text)
    assert was_translated is False
    assert result_text == text


def test_french_job_translates_to_english(translator: NllbTranslator):
    text = (
        "## Description du sujet\n\n"
        "Ce projet de doctorat vise à explorer la conversion optique non linéaire."
    )
    result_text, was_translated = translator.translate(text)
    assert was_translated is True
    assert "## Description of the subject" in result_text
    assert "quantum" not in result_text.lower() or "conversion" in result_text.lower()


def test_hybrid_document_preserves_english_sections(translator: NllbTranslator):
    text = (
        "## Description du sujet\n\n"
        "Ce projet vise à explorer la conversion optique.\n\n"
        "---\n\n"
        "Nonlinear optical phenomena play a crucial role in modern communications.\n\n"
        "-Master 2 de Physique\n"
        "-Good knowledge of Quantum Physics"
    )
    result_text, was_translated = translator.translate(text)
    assert was_translated is True
    # French parts translated
    assert "## Description of the subject" in result_text
    assert "Master 2 in physics" in result_text
    # English parts preserved untouched
    assert (
        "Nonlinear optical phenomena play a crucial role in modern communications." in result_text
    )
    assert "Good knowledge of Quantum Physics" in result_text
    # Divider line preserved
    assert "---" in result_text
