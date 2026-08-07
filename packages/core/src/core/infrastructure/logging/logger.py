import json
import logging
import os
from datetime import UTC, datetime

SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


def _success(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)


if not hasattr(logging.Logger, "success"):
    logging.Logger.success = _success


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(UTC).isoformat(),
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
        import sys
        from logging.handlers import RotatingFileHandler

        log_file = os.getenv("LOG_FILE", "agent.log")
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        try:
            handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
        except Exception as e:
            sys.stderr.write(f"Warning: Could not create RotatingFileHandler for {log_file}: {e}\n")

        # Add stdout stream handler for Docker log aggregation
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(JsonFormatter())
        logger.addHandler(stream_handler)

        logger.setLevel(logging.INFO)

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "agent"):
            record.agent = agent_name
        return record

    logging.setLogRecordFactory(record_factory)
    return logger
