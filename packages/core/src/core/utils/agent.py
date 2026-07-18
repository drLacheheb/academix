import os
import signal
import logging
import threading
from typing import Callable

logger = logging.getLogger("core.agent")

# Global event for coordinating process termination
shutdown_event = threading.Event()


def handle_shutdown(signum, frame):
    logger.info(f"Signal {signum} received. Triggering graceful shutdown...")
    shutdown_event.set()


# Register standard OS signals for clean exit
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
if hasattr(signal, "SIGBREAK"):  # Windows support
    signal.signal(signal.SIGBREAK, handle_shutdown)


def run_agent_loop(cycle_fn: Callable[[], bool | None], default_interval: float = 10.0):
    """
    Executes an agent cycle periodically, listening for OS shutdown signals.
    If cycle_fn returns True, it loops immediately without sleeping.
    """
    interval = float(os.environ.get("AGENT_POLL_INTERVAL", str(default_interval)))

    logger.info(f"Starting agent loop with interval: {interval}s")
    while not shutdown_event.is_set():
        work_done = False
        try:
            result = cycle_fn()
            if result is True:
                work_done = True
        except Exception as e:
            logger.error(f"Error during agent cycle execution: {e}")

        if shutdown_event.is_set():
            break

        if not work_done:
            shutdown_event.wait(interval)
    logger.info("Agent loop terminated cleanly.")
