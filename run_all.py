import os
import signal
import sys
import threading
import time

from core.infrastructure.logging.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("unified-supervisor")
shutdown_event = threading.Event()


def run_worker_safe(target_func, worker_name: str):
    logger.info(f"Starting worker: {worker_name}")
    while not shutdown_event.is_set():
        try:
            target_func()
        except Exception as e:
            if shutdown_event.is_set():
                break
            logger.error(f"Worker {worker_name} crashed with error: {e}. Restarting in 5s...")
            time.sleep(5)


def start_all_workers():
    workers = []

    # 1. Telegram Bot (Long polling)
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        try:
            from telegram_bot.main import run_polling

            t_bot = threading.Thread(
                target=run_worker_safe,
                args=(run_polling, "telegram-bot"),
                daemon=True,
                name="Worker-TelegramBot",
            )
            workers.append(t_bot)
        except Exception as e:
            logger.warning(f"Could not initialize Telegram Bot worker: {e}")

    # 2. Refinement Worker (OmniRoute LLM Extraction)
    try:
        from agent_refinement.main import run as run_refinement

        t_ref = threading.Thread(
            target=run_worker_safe,
            args=(run_refinement, "refinement-worker"),
            daemon=True,
            name="Worker-Refinement",
        )
        workers.append(t_ref)
    except Exception as e:
        logger.warning(f"Could not initialize Refinement worker: {e}")

    # 3. Matching Worker (Multi-factor scoring)
    try:
        from agent_matching.main import run as run_matching

        t_match = threading.Thread(
            target=run_worker_safe,
            args=(run_matching, "matching-worker"),
            daemon=True,
            name="Worker-Matching",
        )
        workers.append(t_match)
    except Exception as e:
        logger.warning(f"Could not initialize Matching worker: {e}")

    # 4. Embedding Worker (Nomic vector generation)
    try:
        from agent_embedding.main import run as run_embedding

        t_emb = threading.Thread(
            target=run_worker_safe,
            args=(run_embedding, "embedding-worker"),
            daemon=True,
            name="Worker-Embedding",
        )
        workers.append(t_emb)
    except Exception as e:
        logger.warning(f"Could not initialize Embedding worker: {e}")

    # 5. CV Parsing Worker (PDF extractor)
    try:
        from agent_cv_parsing.main import run as run_cv_parsing

        t_cv = threading.Thread(
            target=run_worker_safe,
            args=(run_cv_parsing, "cv-parsing-worker"),
            daemon=True,
            name="Worker-CvParsing",
        )
        workers.append(t_cv)
    except Exception as e:
        logger.warning(f"Could not initialize CV Parsing worker: {e}")

    # 6. Translation Worker (NLLB multi-lingual engine)
    try:
        from agent_translation.main import run as run_translation

        t_trans = threading.Thread(
            target=run_worker_safe,
            args=(run_translation, "translation-worker"),
            daemon=True,
            name="Worker-Translation",
        )
        workers.append(t_trans)
    except Exception as e:
        logger.warning(f"Could not initialize Translation worker: {e}")

    # 7. Cleanup Agent (Expired/404 purger)
    try:
        from agent_cleanup.main import run as run_cleanup

        t_clean = threading.Thread(
            target=run_worker_safe,
            args=(run_cleanup, "cleanup-agent"),
            daemon=True,
            name="Worker-Cleanup",
        )
        workers.append(t_clean)
    except Exception as e:
        logger.warning(f"Could not initialize Cleanup worker: {e}")

    # 8. Sourcing & Discovery Crawlers
    crawler_modules = [
        ("abg-discovery", "abg_discovery.main"),
        ("abg-sourcing", "abg_sourcing.main"),
        ("academictransfer-discovery", "academictransfer_discovery.main"),
        ("academictransfer-sourcing", "academictransfer_sourcing.main"),
        ("euraxess-discovery", "euraxess_discovery.main"),
        ("euraxess-sourcing", "euraxess_sourcing.main"),
        ("naturecareers-discovery", "naturecareers_discovery.main"),
        ("naturecareers-sourcing", "naturecareers_sourcing.main"),
        ("researchgate-discovery", "researchgate_discovery.main"),
        ("researchgate-sourcing", "researchgate_sourcing.main"),
        ("eurosciencejobs-discovery", "eurosciencejobs_discovery.main"),
        ("eurosciencejobs-sourcing", "eurosciencejobs_sourcing.main"),
    ]

    for name, mod_path in crawler_modules:
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            if hasattr(mod, "run"):
                t_c = threading.Thread(
                    target=run_worker_safe,
                    args=(mod.run, name),
                    daemon=True,
                    name=f"Crawler-{name}",
                )
                workers.append(t_c)
        except Exception as e:
            logger.warning(f"Could not initialize crawler {name}: {e}")

    # Launch all workers
    for w in workers:
        w.start()

    logger.info(f"Successfully launched {len(workers)} background agent workers.")
    return workers


def handle_shutdown(signum, frame):
    logger.info(f"Received shutdown signal ({signum}). Terminating all workers...")
    shutdown_event.set()
    sys.exit(0)


def wait_for_api_ready(port: int, max_wait: float = 30.0) -> bool:
    import urllib.request

    url = f"http://127.0.0.1:{port}/health"
    start = time.time()
    while time.time() - start < max_wait and not shutdown_event.is_set():
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    port = int(os.environ.get("PORT", "8000"))
    os.environ["API_URL"] = f"http://127.0.0.1:{port}"
    logger.info(
        f"Starting Academix Unified Server on port {port} (API_URL: {os.environ['API_URL']})..."
    )

    # Start FastAPI server in a dedicated thread
    import uvicorn

    config = uvicorn.Config(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    t_server = threading.Thread(target=server.run, daemon=True, name="FastAPI-Server")
    t_server.start()

    # Wait for API server to become healthy before launching worker loops
    logger.info(f"Waiting for API server to initialize on port {port}...")
    if wait_for_api_ready(port):
        logger.success(f"FastAPI server online and healthy on port {port}.")
    else:
        logger.warning(
            f"FastAPI server health check timed out on port {port}. Starting workers anyway."
        )

    # Start all background workers
    start_all_workers()

    # Keep main thread alive until shutdown
    while not shutdown_event.is_set():
        time.sleep(1)

    server.should_exit = True


if __name__ == "__main__":
    main()
