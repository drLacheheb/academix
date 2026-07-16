import os
import json
import ctranslate2
import sentencepiece as spm


class NllbTranslator:
    def __init__(self, model_path: str):
        self._translator = ctranslate2.Translator(model_path, device="cpu")
        sp_path = f"{model_path}/sentencepiece.bpe.model"
        self._sp = spm.SentencePieceProcessor(sp_path)

        # Load language mapping from JSON file
        json_path = os.path.join(os.path.dirname(__file__), "languages.json")
        with open(json_path, "r", encoding="utf-8") as f:
            self._lang_map = json.load(f)

    def translate(self, text: str, source_lang: str) -> str:
        if not text or not text.strip():
            return text
        src_code = self._lang_map.get(source_lang)
        if not src_code:
            return text  # Unknown language -> return as-is

        paragraphs = text.split("\n")
        translated_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                translated_paragraphs.append("")
                continue

            # Split paragraph into sentences
            import re

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
                output_tokens = results[0].hypotheses[0][1:]  # Skip lang token
                translated_sentences.append(self._sp.decode(output_tokens))
            translated_paragraphs.append(" ".join(translated_sentences))

        return "\n".join(translated_paragraphs)
