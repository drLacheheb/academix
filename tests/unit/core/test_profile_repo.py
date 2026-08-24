from datetime import datetime, timedelta

from core.domain.models.profile import CandidateProfile
from core.infrastructure.db.models import CandidateProfileModel
from core.infrastructure.db.pipeline_repository import PipelineJobRepository


def test_submit_raw_text_transitions_to_pending_translation(memory_repo: PipelineJobRepository):
    # Ingest a placeholder CV
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Marie Curie",
            email="marie@curie.fr",
            cv_file_path="/uploads/cv.pdf",
            status="PENDING_INGESTION",
        )
    )
    profile_id = saved.id
    assert profile_id is not None

    # CV parsing parses raw text
    memory_repo.profiles.submit_raw_text(
        profile_id=profile_id,
        raw_text="Curriculum Vitae: Marie Curie, PhD in Physics. Research on Radioactivity.",
        name="Marie Curie",
        email="marie@curie.fr",
    )

    session = memory_repo._SessionLocal()
    profile = (
        session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
    )
    assert profile is not None
    assert profile.status == "PENDING_TRANSLATION"
    assert profile.raw_text is not None
    session.close()


def test_profile_translation_flow(memory_repo: PipelineJobRepository):
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Pierre Curie",
            email="pierre@curie.fr",
            cv_file_path="/uploads/cv2.pdf",
            status="PENDING_INGESTION",
        )
    )
    profile_id = saved.id
    assert profile_id is not None
    memory_repo.profiles.submit_raw_text(profile_id, "Doctorat de Physique de l'ESPCI.")

    # Claim for translation
    stale_cutoff = datetime.now() - timedelta(minutes=5)
    claimed = memory_repo.profiles.claim_next_for_translation("worker-1", stale_cutoff)
    assert claimed is not None
    assert claimed.id == profile_id

    # Complete translation with translated text
    memory_repo.profiles.complete_translation(profile_id, "PhD in Physics from ESPCI.")

    session = memory_repo._SessionLocal()
    profile = (
        session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
    )
    assert profile is not None
    assert profile.raw_text_en == "PhD in Physics from ESPCI."
    assert profile.status == "PENDING_REFINEMENT"
    session.close()


def test_profile_translation_skips_english(memory_repo: PipelineJobRepository):
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Alan Turing",
            email="alan@cam.ac.uk",
            cv_file_path="/uploads/cv3.pdf",
            status="PENDING_INGESTION",
        )
    )
    profile_id = saved.id
    assert profile_id is not None
    memory_repo.profiles.submit_raw_text(profile_id, "PhD in Mathematics from Cambridge.")

    stale_cutoff = datetime.now() - timedelta(minutes=5)
    claimed = memory_repo.profiles.claim_next_for_translation("worker-1", stale_cutoff)
    assert claimed is not None

    # Complete translation with None (skipped)
    memory_repo.profiles.complete_translation(profile_id, None)

    session = memory_repo._SessionLocal()
    profile = (
        session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
    )
    assert profile is not None
    assert profile.raw_text_en is None
    assert profile.status == "PENDING_REFINEMENT"
    session.close()
