import functools
import os
import time

import requests
from core.infrastructure.logging.logger import get_logger
from core.utils.formatters import format_match_card, format_profile_card

logger = get_logger("telegram-decorators")

# In-memory TTL cache for blocked or invalid chat IDs: {chat_id: expiry_timestamp}
_BLOCKED_CHAT_IDS: dict[str, float] = {}
_DEFAULT_BLOCK_TTL_SECONDS: float = 3600.0


def _is_chat_blocked(chat_id: int | str) -> bool:
    cid = str(chat_id)
    expiry = _BLOCKED_CHAT_IDS.get(cid)
    if expiry is None:
        return False
    if time.time() > expiry:
        _BLOCKED_CHAT_IDS.pop(cid, None)
        return False
    return True


def _mark_chat_blocked(chat_id: int | str, ttl_seconds: float = _DEFAULT_BLOCK_TTL_SECONDS) -> None:
    _BLOCKED_CHAT_IDS[str(chat_id)] = time.time() + ttl_seconds


def unblock_chat(chat_id: int | str) -> None:
    _BLOCKED_CHAT_IDS.pop(str(chat_id), None)


class TelegramSendResult:
    def __init__(
        self,
        success: bool,
        status_code: int | None = None,
        error_message: str | None = None,
    ):
        self.success = success
        self.status_code = status_code
        self.error_message = error_message

    @property
    def is_permanent_failure(self) -> bool:
        return self.status_code in (400, 403)

    def __bool__(self) -> bool:
        return self.success


def send_telegram_message(chat_id: int | str, text: str) -> TelegramSendResult:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set in environment. Skipping Telegram dispatch.")
        return TelegramSendResult(success=False, error_message="TELEGRAM_BOT_TOKEN missing")

    if _is_chat_blocked(chat_id):
        return TelegramSendResult(
            success=False,
            status_code=403,
            error_message="Chat ID is cached as blocked/forbidden.",
        )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Successfully sent Telegram notification to chat_id={chat_id}")
            return TelegramSendResult(success=True, status_code=200)

        if resp.status_code in (400, 403):
            _mark_chat_blocked(chat_id)
            logger.warning(
                f"Telegram delivery permanently failed for chat_id={chat_id}: "
                f"status={resp.status_code}, response={resp.text}"
            )
            return TelegramSendResult(
                success=False,
                status_code=resp.status_code,
                error_message=resp.text,
            )

        logger.error(
            f"Failed to send Telegram message to chat_id={chat_id}: "
            f"status={resp.status_code}, response={resp.text}"
        )
        return TelegramSendResult(
            success=False,
            status_code=resp.status_code,
            error_message=resp.text,
        )
    except Exception as e:
        logger.error(f"Exception sending Telegram message to chat_id={chat_id}: {e}")
        return TelegramSendResult(success=False, error_message=str(e))


def notify_telegram_on_cv_completion(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)

        try:
            profile = None
            if isinstance(result, dict):
                if "profile" in result and isinstance(result["profile"], dict):
                    profile = result["profile"]
                elif "telegram_chat_id" in result:
                    profile = result

            # If result only returned profile_id (e.g. {"status": "success", "profile_id": 1})
            if not profile:
                profile_id = None
                if isinstance(result, dict) and "profile_id" in result:
                    profile_id = result["profile_id"]
                elif "body" in kwargs and hasattr(kwargs["body"], "profile_id"):
                    profile_id = kwargs["body"].profile_id

                if profile_id:
                    from api.config import get_database_url
                    from core.infrastructure.db.pipeline_repository import PipelineJobRepository

                    repo = PipelineJobRepository(get_database_url())
                    p = repo.profiles.get_by_id(int(profile_id))
                    if p:
                        profile = p.to_dict()

            if profile and isinstance(profile, dict):
                chat_id = profile.get("telegram_chat_id")
                prof_id = profile.get("id") or profile.get("profile_id", "")
                if chat_id:
                    card_body = format_profile_card(profile)
                    header = f"<b>CV Processing Complete! (Profile #{prof_id})</b>\n\n"
                    full_msg = f"{header}{card_body}"
                    send_telegram_message(chat_id, full_msg)
        except Exception as e:
            logger.error(f"Error in notify_telegram_on_cv_completion decorator: {e}")

        return result

    return wrapper


def notify_telegram_on_matches_found(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)

        try:
            from api.config import get_database_url
            from core.infrastructure.db.pipeline_repository import PipelineJobRepository

            repo = PipelineJobRepository(get_database_url())
            matches = []
            if isinstance(result, list):
                matches = result
            elif isinstance(result, dict) and "matches" in result:
                matches = result["matches"]
            elif isinstance(result, dict) and "match" in result:
                matches = [result["match"]]

            # If result only returned match_id or task_id (e.g. {"status": "completed"})
            if not matches:
                match_id = None
                if isinstance(result, dict) and "match_id" in result:
                    match_id = result["match_id"]
                elif "body" in kwargs and hasattr(kwargs["body"], "match_id"):
                    match_id = kwargs["body"].match_id

                if match_id:
                    unnotified = repo.matches.get_unnotified_matches(limit=20)
                    matches = [m for m in unnotified if m.get("match_id") == int(match_id)]
                else:
                    # Called from /matches/complete (body has task_id and matches)
                    matches = repo.matches.get_unnotified_matches(limit=20)

            for m in matches:
                if not isinstance(m, dict):
                    continue
                chat_id = m.get("telegram_chat_id")
                if not chat_id:
                    continue

                msg = format_match_card(m)
                res = send_telegram_message(chat_id, msg)
                is_success = bool(res.success) if hasattr(res, "success") else bool(res)
                is_perm = getattr(res, "is_permanent_failure", False)
                if is_success or is_perm:
                    if "match_id" in m:
                        repo.matches.mark_as_notified([m["match_id"]])
        except Exception as e:
            logger.error(f"Error in notify_telegram_on_matches_found decorator: {e}")

        return result

    return wrapper
