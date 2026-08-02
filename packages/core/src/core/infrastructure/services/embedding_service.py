import math

from core.domain.interfaces.services import BaseEmbeddingService
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-embedding-service")


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


class EmbeddingService(BaseEmbeddingService):
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            import os

            from sentence_transformers import SentenceTransformer

            embedding_model = os.environ.get("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
            models_dir = os.environ.get("MODELS_DIR", "models")

            logger.info(
                f"Loading embedding model '{embedding_model}' with cache_folder "
                f"'{models_dir}' into memory..."
            )
            cls._model = SentenceTransformer(
                embedding_model, cache_folder=models_dir, trust_remote_code=True
            )
            logger.info("Embedding model loaded successfully!")
        return cls._model

    def encode_text(self, text: str) -> list[float]:
        if not text.strip():
            return [0.0] * 256

        # Prefix required by nomic-embed-text series
        prefixed_text = f"search_document: {text}"

        # Load and compute raw embedding (768 dimensions)
        model = self.get_model()
        raw_embedding = model.encode(prefixed_text).tolist()

        # Matryoshka truncation to 256 dimensions + L2 normalization
        truncated = raw_embedding[:256]
        return l2_normalize(truncated)

    def encode_skills(self, skills: list[str] | None) -> list[float] | None:
        if not skills:
            return None
        # Join skills with commas to make a descriptive string
        text = ", ".join(skills)
        return self.encode_text(text)

    def encode_research(self, interests: list[str] | None, title: str = "") -> list[float] | None:
        if not interests and not title:
            return None
        parts = []
        if title:
            parts.append(title)
        if interests:
            parts.append(", ".join(interests))
        text = " ".join(parts)
        return self.encode_text(text)
