import json
import logging
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "agent": getattr(record, "agent", "unknown"),
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["error"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(agent_name: str) -> logging.Logger:
    logger = logging.getLogger(f"agent.{agent_name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "agent"):
            record.agent = agent_name
        return record

    logging.setLogRecordFactory(record_factory)
    return logger
