import re

import langcodes
import sentencex
from core.domain.interfaces.services import BaseTranslator
from core.infrastructure.services.lang_detector import LanguageDetector


def to_flores_code(lang_code: str) -> str | None:
    if not lang_code or not lang_code.strip():
        return None
    clean = lang_code.strip()
    if clean.lower() in ["en", "eng", "eng_latn"]:
        return "eng_Latn"
    try:
        tag = langcodes.get(clean).maximize()
        iso3 = tag.to_alpha3()
        script = "Hang" if tag.script == "Kore" else tag.script
        return f"{iso3}_{script}"
    except Exception:
        return None


DATE_REGEX = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$|^\d{4}[./-]\d{1,2}[./-]\d{1,2}$")
DIVIDER_REGEX = re.compile(r"^[-*_]{3,}$")
URL_REGEX = re.compile(r"^https?://\S+$")
PREFIX_REGEX = re.compile(
    r"^((?:#{1,6}\s+|-\s*\*\*[^*]+:\*\*\s*|[-*]\s+|\d+[\.\)]\s+|[a-zA-Z][\.\)]\s+|\([a-zA-Z0-9]+\)\s+))(.*)$"
)


class NllbTranslator(BaseTranslator):
    def __init__(self, model_path: str):
        import ctranslate2
        import sentencepiece as spm

        self._translator = ctranslate2.Translator(model_path, device="cpu")
        sp_path = f"{model_path}/sentencepiece.bpe.model"
        self._sp = spm.SentencePieceProcessor(sp_path)
        self._detector = LanguageDetector()

    def translate(self, text: str) -> tuple[str, bool]:
        if not text or not text.strip():
            return text, False

        paragraphs = text.split("\n")
        translated_paragraphs: list[str] = []
        has_translated_anything = False

        for paragraph in paragraphs:
            p_strip = paragraph.strip()
            if not p_strip:
                translated_paragraphs.append("")
                continue

            # 1. Pass-through non-translatable text: dates, dividers, URLs, metadata
            if (
                DATE_REGEX.match(p_strip)
                or DIVIDER_REGEX.match(p_strip)
                or URL_REGEX.match(p_strip)
                or p_strip.startswith("**Source URL**")
            ):
                translated_paragraphs.append(paragraph)
                continue

            # 2. Extract Markdown list and header prefixes
            prefix = ""
            text_to_translate = p_strip
            header_match = PREFIX_REGEX.match(p_strip)
            if header_match:
                prefix = header_match.group(1)
                text_to_translate = header_match.group(2).strip()

            if (
                not text_to_translate
                or len(text_to_translate) < 3
                or "reference" in prefix.lower()
                or DATE_REGEX.match(text_to_translate)
                or URL_REGEX.match(text_to_translate)
                or (re.search(r"\d{4,}", text_to_translate) and "-" in text_to_translate)
            ):
                translated_paragraphs.append(paragraph)
                continue

            # 3. Detect language per-paragraph
            p_lang = self._detector.detect_lang(text_to_translate)
            if p_lang == "en":
                translated_paragraphs.append(paragraph)
                continue

            src_code = to_flores_code(p_lang)
            if not src_code or src_code == "eng_Latn":
                translated_paragraphs.append(paragraph)
                continue

            # 4. Split non-English paragraph into sentences using sentencex
            try:
                segment_fn = getattr(sentencex, "segment")
                sentences = segment_fn(p_lang, text_to_translate)
            except Exception:
                sentences = re.split(r"(?<=[.!?])\s+", text_to_translate)

            translated_sentences: list[str] = []
            for sentence in sentences:
                s_strip = sentence.strip()
                if not s_strip:
                    continue
                if DATE_REGEX.match(s_strip) or URL_REGEX.match(s_strip):
                    translated_sentences.append(s_strip)
                    continue

                tokens = [src_code] + self._sp.encode(s_strip, out_type=str) + ["</s>"]
                results = self._translator.translate_batch(
                    [tokens],
                    target_prefix=[["eng_Latn"]],
                    beam_size=1,
                )
                output_tokens = results[0].hypotheses[0][1:]
                translated_sentences.append(self._sp.decode(output_tokens))
                has_translated_anything = True

            translated_p = prefix + " ".join(translated_sentences)
            translated_paragraphs.append(translated_p)

        return "\n".join(translated_paragraphs), has_translated_anything
