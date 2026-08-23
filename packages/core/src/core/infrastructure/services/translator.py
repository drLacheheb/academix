import re

import sentencex
from core.domain.interfaces.services import BaseTranslator

FLORES_MAP: dict[str, str] = {
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "nl": "nld_Latn",
    "sv": "swe_Latn",
    "es": "spa_Latn",
    "it": "ita_Latn",
    "pl": "pol_Latn",
    "pt": "por_Latn",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
}


class NllbTranslator(BaseTranslator):
    def __init__(self, model_path: str):
        import ctranslate2
        import sentencepiece as spm

        self._translator = ctranslate2.Translator(model_path, device="cpu")
        sp_path = f"{model_path}/sentencepiece.bpe.model"
        self._sp = spm.SentencePieceProcessor(sp_path)
        self._lang_map = FLORES_MAP

    def translate(self, text: str, source_lang: str) -> str:
        if not text or not text.strip():
            return text
        src_code = self._lang_map.get(source_lang)
        if not src_code:
            return text

        paragraphs = text.split("\n")
        translated_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                translated_paragraphs.append("")
                continue

            try:
                segment_fn = getattr(sentencex, "segment")
                sentences = segment_fn(source_lang, paragraph)
            except Exception:
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            translated_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                tokens = [src_code] + self._sp.encode(sentence, out_type=str) + ["</s>"]
                results = self._translator.translate_batch(
                    [tokens],
                    target_prefix=[["eng_Latn"]],
                    beam_size=1,
                )
                output_tokens = results[0].hypotheses[0][1:]
                translated_sentences.append(self._sp.decode(output_tokens))
            translated_paragraphs.append(" ".join(translated_sentences))

        return "\n".join(translated_paragraphs)
