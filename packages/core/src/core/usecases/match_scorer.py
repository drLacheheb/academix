from collections.abc import Sequence

from core.domain.models.job import Job
from core.domain.models.match import Match
from core.domain.models.profile import CandidateProfile
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-match-scorer")


LANGUAGE_NAMES = {
    "de": ["german", "deutsch", "de"],
    "fr": ["french", "français", "francais", "fr"],
    "pl": ["polish", "polski", "pl"],
    "es": ["spanish", "español", "espanol", "es"],
    "nl": ["dutch", "nederlands", "nl"],
    "it": ["italian", "italiano", "it"],
    "en": ["english", "en"],
}


def parse_degree(degree_str: str | None) -> int:
    """Map education levels to comparable ranks: PhD=3, Master=2, Bachelor=1, None=0."""
    if not degree_str:
        return 0
    s = degree_str.lower()
    if "phd" in s or "ph.d" in s or "doctor" in s or "dr." in s:
        return 3

    import re

    if (
        "master" in s
        or "msc" in s
        or "m.sc" in s
        or re.search(r"\bma\b", s)
        or re.search(r"\bm\.a\b", s)
    ):
        return 2
    if (
        "bachelor" in s
        or "bsc" in s
        or "b.sc" in s
        or re.search(r"\bba\b", s)
        or re.search(r"\bb\.a\b", s)
    ):
        return 1
    return 0


def check_degree_eligibility(candidate_degree: str | None, job_education_level: str | None) -> bool:
    """Returns True if candidate's degree is equal to or higher than job's required degree."""
    if not job_education_level or job_education_level.lower() in [
        "none",
        "any",
        "unspecified",
    ]:
        return True
    return parse_degree(candidate_degree) >= parse_degree(job_education_level)


def check_language_eligibility(
    candidate_languages: Sequence[dict[str, str] | str] | None,
    job_language_code: str | None,
) -> bool:
    """Returns True if the candidate speaks the language required by the job."""
    if not job_language_code or job_language_code.lower() in ["en", "english"]:
        return True
    if not candidate_languages:
        return False

    code = job_language_code.lower()
    allowed_names = LANGUAGE_NAMES.get(code, [code])

    for item in candidate_languages:
        if isinstance(item, dict):
            lang_name = item.get("language", "").lower()
        elif isinstance(item, str):
            lang_name = item.lower()
        else:
            continue
        if any(name in lang_name for name in allowed_names):
            return True
    return False


def dot_product(v1: list[float] | None, v2: list[float] | None) -> float:
    """Calculates dot product of two L2-normalized vectors (equivalent to cosine similarity)."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    return sum(x * y for x, y in zip(v1, v2))


class MatchScorer:
    @staticmethod
    def score_candidate_against_job(
        candidate: CandidateProfile,
        job: Job,
        threshold: float = 0.3,
    ) -> Match | None:
        # 1. Hard Filter: Degree Eligibility
        degree_ok = check_degree_eligibility(candidate.highest_degree, job.education_level)
        if not degree_ok:
            return None

        # 2. Hard Filter: Semantic Degree Field Match
        if candidate.degree_embedding and job.degree_embedding:
            degree_field_score = dot_product(candidate.degree_embedding, job.degree_embedding)
            if degree_field_score < 0.65:
                # Degree fields are too semantically divergent (e.g. CS vs Biology)
                return None

        # 3. Hard Filter: Language Eligibility
        lang_ok = check_language_eligibility(candidate.languages, job.language_code)
        if not lang_ok:
            return None

        # 4. Soft Scores: Semantic similarity via pre-computed embeddings
        skill_score = dot_product(candidate.skill_embedding, job.skill_embedding)
        research_score = dot_product(candidate.research_embedding, job.research_embedding)

        # 5. Composite Score: Max-Dominance Asymmetric Pooling (Approach A)
        max_score = max(skill_score, research_score)
        min_score = min(skill_score, research_score)
        composite_score = 0.70 * max_score + 0.30 * min_score

        # Bound composite score to [0.0, 1.0]
        composite_score = max(0.0, min(1.0, composite_score))

        if composite_score < threshold or candidate.id is None:
            return None

        return Match(
            candidate_id=candidate.id,
            job_url=job.url,
            score=round(composite_score, 4),
            degree_eligible=True,
            language_eligible=True,
            skill_score=round(skill_score, 4),
            research_score=round(research_score, 4),
        )
