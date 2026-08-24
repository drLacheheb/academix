import os

from core.domain.constants import JobStatus
from core.domain.models.job import Job
from core.infrastructure.db.models import CandidateProfileModel, JobModel, JobOrchestrationModel
from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from core.infrastructure.services.translator import NllbTranslator

MODEL_PATH = os.path.abspath("models/mijuanlo/nllb-200-distilled-600M-ct2-int8")
MODEL_EXISTS = os.path.exists(os.path.join(MODEL_PATH, "model.bin"))


def test_full_e2e_job_pipeline_flow(memory_repo: PipelineJobRepository):
    # 1. Job Sourcing
    french_job = Job(
        title="Postdoctorant en photonique quantique",
        url="https://example.com/e2e-job-1",
        source="abg",
        employer="ESPCI Paris",
        city="Paris",
        country="France",
        job_details=(
            "## Description du sujet\n\n"
            "Ce projet de doctorat vise à explorer la conversion optique."
        ),
    )
    memory_repo.save([french_job])

    # 2. Translation Worker Step
    claimed_job = memory_repo.claim_next_for_translation("translation-worker-1")
    assert claimed_job is not None
    assert claimed_job.url == french_job.url

    if MODEL_EXISTS:
        translator = NllbTranslator(MODEL_PATH)
        translated_text, was_translated = translator.translate(claimed_job.job_details or "")
        assert was_translated is True
    else:
        translated_text = (
            "## Description of the subject\n\n"
            "This doctoral project aims to explore optical conversion."
        )

    memory_repo.complete_translation(
        url=claimed_job.url,
        job_details_en=translated_text,
    )

    # 3. Refinement Worker Step
    claimed_ref = memory_repo.claim_next_for_refinement("refinement-worker-1")
    assert claimed_ref is not None
    assert claimed_ref.url == french_job.url

    memory_repo.complete_refinement(
        url=claimed_ref.url,
        required_skills=["Photonics", "Quantum Optics", "Physics"],
        education_level="PhD",
        degree_fields=["Physics"],
        city="Paris",
        country="France",
    )

    # 4. Embedding Worker Step
    claimed_emb = memory_repo.claim_next_for_embedding("embedding-worker-1")
    assert claimed_emb is not None
    assert claimed_emb.url == french_job.url

    dummy_skill_emb = [0.1] * 768
    dummy_res_emb = [0.2] * 768
    dummy_deg_emb = [0.3] * 768

    memory_repo.complete_embedding(
        url=claimed_emb.url,
        skill_embedding=dummy_skill_emb,
        research_embedding=dummy_res_emb,
        degree_embedding=dummy_deg_emb,
    )

    # Verify Final DB State
    session = memory_repo._SessionLocal()
    job = session.query(JobModel).filter(JobModel.url == french_job.url).first()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == french_job.url)
        .first()
    )

    assert job is not None
    assert orch is not None
    assert job.job_details_en is not None
    assert orch.translation_status == JobStatus.COMPLETED
    assert orch.refinement_status == JobStatus.COMPLETED
    assert orch.embedding_status == JobStatus.COMPLETED
    session.close()


def test_full_e2e_profile_pipeline_flow(memory_repo: PipelineJobRepository):
    from datetime import datetime, timedelta

    from core.domain.models.profile import CandidateProfile

    # 1. Candidate CV Ingestion
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Marie Curie",
            email="marie@curie.fr",
            cv_file_path="/uploads/curie_cv.pdf",
            status="PENDING_INGESTION",
        )
    )
    profile_id = saved.id
    assert profile_id is not None

    memory_repo.profiles.submit_raw_text(
        profile_id=profile_id,
        raw_text=(
            "Curriculum Vitae: Marie Curie.\n\n"
            "Je suis chercheuse titulaire d'un doctorat en physique et chimie "
            "de la faculté des sciences de Paris, "
            "spécialisée dans l'étude des rayonnements radioactifs."
        ),
    )

    # 2. Candidate Profile Translation
    stale_cutoff = datetime.now() - timedelta(minutes=5)
    claimed_prof = memory_repo.profiles.claim_next_for_translation(
        "translation-worker-1", stale_cutoff
    )
    assert claimed_prof is not None

    if MODEL_EXISTS:
        translator = NllbTranslator(MODEL_PATH)
        trans_cv, was_trans = translator.translate(claimed_prof.raw_text or "")
        assert was_trans is True
    else:
        trans_cv = (
            "Curriculum Vitae: Marie Curie.\n\n"
            "I am a researcher with a doctorate in physics and chemistry..."
        )

    memory_repo.profiles.complete_translation(profile_id, trans_cv)

    # 3. Candidate Profile Refinement
    claimed_ref_prof = memory_repo.profiles.claim_next_for_refinement(
        "refinement-worker-1", stale_cutoff
    )
    assert claimed_ref_prof is not None

    refined_domain = CandidateProfile(
        id=profile_id,
        name="Marie Curie",
        email="marie@curie.fr",
        highest_degree="PhD",
        skills=["Radioactivity", "Physics"],
        degree_fields=["Physics"],
    )
    memory_repo.profiles.complete_refinement(profile_id, refined_domain)

    # 4. Candidate Profile Embedding
    claimed_emb_prof = memory_repo.profiles.claim_next_for_embedding(
        "embedding-worker-1", stale_cutoff
    )
    assert claimed_emb_prof is not None

    memory_repo.profiles.complete_embedding(
        profile_id=profile_id,
        skill_embedding=[0.1] * 768,
        research_embedding=[0.2] * 768,
        degree_embedding=[0.3] * 768,
    )

    session = memory_repo._SessionLocal()
    prof_db = (
        session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
    )

    assert prof_db is not None
    assert prof_db.raw_text_en is not None
    assert prof_db.highest_degree == "PhD"
    assert prof_db.skill_embedding is not None
    assert prof_db.status == "COMPLETED"
    session.close()
