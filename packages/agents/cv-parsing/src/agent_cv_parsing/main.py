import os
import sys
import logging
import gc
import socket
import json
import httpx
from dotenv import load_dotenv

from core.utils.agent import run_agent_loop
from core.utils.api import make_api_client
from core.domain.models.profile import CandidateProfile
from core.infrastructure.services.pdf_parser import (
    parse_pdf_to_markdown,
    truncate_bibliography,
)
from core.infrastructure.services.lang_detector import LanguageDetector
from core.infrastructure.services.translator import NllbTranslator
from core.infrastructure.services.embedding_service import EmbeddingService
from core.infrastructure.services.llm_runner import LocalLlmRunner
from core.infrastructure.services.storage import get_storage_service_from_env

# Ensure stdout uses UTF-8 to prevent encoding crashes on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s",
)
logger = logging.getLogger("agent.cv-parsing")

AGENT_NAME = f"{os.environ.get('AGENT_NAME', 'cv-parsing-worker')}-{socket.gethostname()}"


def get_llm_runner() -> LocalLlmRunner:
    models_dir = os.environ.get("MODELS_DIR", "models")
    model_path = os.environ.get(
        "MODEL_PATH", "unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf"
    )
    resolved_path = os.path.abspath(os.path.join(models_dir, model_path))

    max_context = int(os.environ.get("MAX_LENGTH", "4096"))
    temperature = float(os.environ.get("TEMPERATURE", "0.0"))

    return LocalLlmRunner(
        model_path=resolved_path,
        models_dir=models_dir,
        max_context=max_context,
        temperature=temperature,
    )


def process_ingestion_task(client: httpx.Client) -> bool:
    try:
        response = client.post(
            "/profiles/claim-ingest", json={"agent_name": AGENT_NAME}
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as e:
        logger.error(f"Failed to poll/claim CV ingestion task from API: {e}")
        return False

    profile_data = payload.get("profile")
    if not profile_data:
        return False  # No task pending

    profile_id = profile_data["id"]
    file_path = profile_data["cv_file_path"]
    logger.info(
        f"Successfully claimed CV Ingestion Task for Profile ID: {profile_id} (File: {file_path})"
    )

    local_file_path = None
    is_temp_file = False

    try:
        storage_service = get_storage_service_from_env()
        local_file_path, is_temp_file = storage_service.get_local_path(file_path)
        if not local_file_path or not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Resolved file path {local_file_path} not found on disk.")
    except Exception as e:
        error_msg = f"Failed to retrieve CV file path for {file_path}: {e}"
        logger.error(error_msg, exc_info=True)
        try:
            client.put(
                f"/profiles/fail-ingest/{profile_id}", json={"error_message": error_msg}
            )
        except Exception as api_err:
            logger.error(f"Failed to submit failure status to API: {api_err}")
        return True

    try:
        # Step 1: Parse PDF to markdown text using Docling layout analyzer
        logger.info(
            f"[{profile_id}] Extracting layout and parsing PDF to markdown using Docling..."
        )
        raw_markdown = parse_pdf_to_markdown(local_file_path)

        # Step 2: Detect language of the resume
        logger.info(f"[{profile_id}] Detecting CV language...")
        detector = LanguageDetector()
        lang = detector.detect_lang(raw_markdown)
        logger.info(f"[{profile_id}] Detected language: '{lang}'")

        text_to_extract = raw_markdown

        # Step 3: Translate non-English CVs to English using NLLB-200 and sentencex
        if lang != "en":
            logger.info(
                f"[{profile_id}] Non-English CV detected. Lazily loading NLLB translator..."
            )
            nllb_model_path = os.environ.get(
                "NLLB_MODEL_PATH", "mijuanlo/nllb-200-distilled-600M-ct2-int8"
            )
            models_dir = os.environ.get("MODELS_DIR", "models")
            resolved_nllb_dir = os.path.abspath(
                os.path.join(models_dir, nllb_model_path)
            )

            if os.path.exists(resolved_nllb_dir) and os.path.exists(
                os.path.join(resolved_nllb_dir, "model.bin")
            ):
                translator = NllbTranslator(resolved_nllb_dir)
                logger.info(f"[{profile_id}] Translating CV to English...")
                text_to_extract = translator.translate(raw_markdown, lang)
                logger.info(f"[{profile_id}] Translation completed successfully.")
                # Force cleanup of translation model to save memory before loading Gemma-4
                del translator
            else:
                logger.warning(
                    f"NLLB model directory not found at {resolved_nllb_dir}. Falling back to raw direct LLM extraction."
                )

        # Step 4: Truncate long publication sections
        truncated_markdown = truncate_bibliography(text_to_extract)

        # Step 5: Read extraction prompt template
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "core",
            "src",
            "core",
            "infrastructure",
            "services",
            "prompts",
            "cv_extraction_prompt.txt",
        )
        # Fallback to local import folder check
        if not os.path.exists(prompt_path):
            prompt_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "cv_extraction_prompt.txt")
            )
            if not os.path.exists(prompt_path):
                # Inline fallback prompt if file path can't be resolved in dev
                with open(
                    os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "..",
                            "..",
                            "..",
                            "..",
                            "packages",
                            "core",
                            "src",
                            "core",
                            "infrastructure",
                            "services",
                            "prompts",
                            "cv_extraction_prompt.txt",
                        )
                    ),
                    "r",
                    encoding="utf-8",
                ) as f:
                    system_prompt = f.read().strip()
            else:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read().strip()
        else:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read().strip()

        # Step 6: Initialize Gemma-4 LLM and run extraction
        logger.info(f"[{profile_id}] Lazily loading Gemma-4 LLM runner...")
        runner = get_llm_runner()
        logger.info(f"[{profile_id}] Running LLM skills and metadata extraction...")
        raw_response = runner.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Candidate CV Text:\n\n{truncated_markdown}",
                },
            ],
            max_tokens=2048,
        )
        logger.info(
            f"[{profile_id}] Received response from Gemma-4. Freeing LLM memory..."
        )
        runner.free_model()
        del runner

        # Clean response string if wrapped in markdown formatting ticks
        cleaned_response = raw_response
        if cleaned_response.startswith("```"):
            lines = cleaned_response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_response = "\n".join(lines).strip()

        parsed_data = json.loads(cleaned_response)
        parsed_data["cv_file_path"] = os.path.basename(file_path)
        parsed_data["raw_text"] = raw_markdown

        # Step 7: Parse into domain dataclass and compute embeddings
        profile = CandidateProfile.from_dict(parsed_data)

        logger.info(
            f"[{profile_id}] Computing semantic embeddings for skills and research interests..."
        )
        embedding_service = EmbeddingService()
        profile.skill_embedding = embedding_service.encode_skills(profile.skills)
        profile.research_embedding = embedding_service.encode_research(
            profile.research_interests
        )

        # Step 8: Complete task via API
        logger.info(
            f"[{profile_id}] CV Parsing completed successfully. Uploading results to API gateway..."
        )
        client.put(
            f"/profiles/complete-ingest/{profile_id}",
            json={"profile": profile.to_dict()},
        )
        logger.info(f"[{profile_id}] Profile fully processed and registered!")

    except Exception as e:
        logger.error(
            f"Failed to process CV Ingestion Task for Profile ID {profile_id}: {e}",
            exc_info=True,
        )
        try:
            client.put(
                f"/profiles/fail-ingest/{profile_id}", json={"error_message": str(e)}
            )
        except Exception as api_err:
            logger.error(f"Failed to notify API about parsing failure: {api_err}")
    finally:
        if is_temp_file and local_file_path:
            try:
                storage_service.clean_up(local_file_path)
            except Exception as cleanup_err:
                logger.warning(f"[{profile_id}] Failed to clean up temp file {local_file_path}: {cleanup_err}")
        # Force garbage collection to free model weights and layouter caches immediately
        gc.collect()

    return True


def main():
    logger.info(
        f"Starting CV Ingestion and Parsing Worker (agent_name: {AGENT_NAME})..."
    )
    api_client = make_api_client()
    poll_interval = int(os.environ.get("AGENT_POLL_INTERVAL", "10"))

    def cycle() -> bool:
        return process_ingestion_task(api_client)

    run_agent_loop(
        cycle,
        default_interval=poll_interval,
    )


if __name__ == "__main__":
    main()
