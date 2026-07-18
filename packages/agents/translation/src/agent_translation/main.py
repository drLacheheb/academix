import argparse
import os
import sys
import time
from dotenv import load_dotenv

from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from agent_translation.translator import NllbTranslator

load_dotenv()


def get_config() -> dict:
    model_path = os.environ.get(
        "NLLB_MODEL_PATH",
        "mijuanlo/nllb-200-distilled-600M-ct2-int8",
    )
    models_dir = os.environ.get("MODELS_DIR", "models")
    return {
        "model_path": model_path,
        "models_dir": models_dir,
    }


def run():
    parser = argparse.ArgumentParser(description="Job Translation Agent")
    parser.add_argument(
        "--name",
        type=str,
        default=os.environ.get("AGENT_NAME", "translation-worker"),
        help="Custom agent identifier for locking",
    )
    args = parser.parse_args()

    logger = get_logger(args.name)
    config = get_config()

    logger.info(f"Starting Job Translation Agent (name: {args.name})")

    translator = None
    api = make_api_client(timeout=60.0)

    try:
        while True:
            logger.info("Polling for pending translation jobs...")
            try:
                resp = api.post("/jobs/claim-translate", json={"agent_name": args.name})
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error polling API: {e}")
                time.sleep(10)
                continue

            data = resp.json()
            job_data = data.get("job")

            if not job_data:
                logger.info(
                    "No pending jobs available. Translation batch completed. Exiting."
                )
                break

            job_title = job_data.get("title")
            job_url = job_data.get("url")
            job_description = job_data.get("description")
            job_requirements = job_data.get("requirements")
            source_lang = job_data.get("language_code")

            logger.info(
                f"Successfully claimed job: {job_title} ({job_url}) [lang: {source_lang}]"
            )

            if translator is None:
                model_path = config["model_path"]
                models_dir = config["models_dir"]
                repo_id = "mijuanlo/nllb-200-distilled-600M-ct2-int8"

                if "/" in model_path:
                    repo_id = model_path
                    resolved_model_dir = os.path.abspath(
                        os.path.join(models_dir, model_path)
                    )
                else:
                    resolved_model_dir = os.path.abspath(
                        os.path.join(models_dir, model_path)
                    )

                if not os.path.exists(resolved_model_dir) or not os.path.exists(
                    os.path.join(resolved_model_dir, "model.bin")
                ):
                    logger.info(
                        f"NLLB model directory '{resolved_model_dir}' not found or incomplete. Downloading model from HF repo {repo_id}..."
                    )
                    try:
                        os.makedirs(os.path.dirname(resolved_model_dir), exist_ok=True)
                        from huggingface_hub import snapshot_download

                        snapshot_download(
                            repo_id=repo_id,
                            local_dir=resolved_model_dir,
                            allow_patterns=["*.json", "*.bin", "*.model"],
                            local_dir_use_symlinks=False,
                        )
                        logger.info("Download complete!")
                    except Exception as e:
                        logger.error(
                            f"Failed to automatically download NLLB model: {e}"
                        )
                        sys.exit(1)

                logger.info(
                    f"First job claimed. Loading NLLB-200 model from '{resolved_model_dir}'..."
                )
                translator = NllbTranslator(resolved_model_dir)
                logger.info("NLLB model loaded successfully!")

            try:
                logger.info(
                    f"Translating description and requirements for: {job_title}..."
                )
                desc_en = translator.translate(job_description or "", source_lang)
                req_en = translator.translate(job_requirements or "", source_lang)

                logger.info("Finished translation. Submitting results...")
                submit_resp = api.put(
                    "/jobs/translate",
                    json={
                        "url": job_url,
                        "description_en": desc_en,
                        "requirements_en": req_en,
                    },
                )
                submit_resp.raise_for_status()
                logger.info("Successfully uploaded translation results")

            except Exception as e:
                logger.error(f"Error during translation processing or upload: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Agent shutting down due to KeyboardInterrupt")
    finally:
        api.close()


if __name__ == "__main__":
    run()
