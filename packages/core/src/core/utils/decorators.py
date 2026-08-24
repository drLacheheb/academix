import functools
import os

import requests
from core.infrastructure.logging.logger import get_logger
from core.utils.formatters import format_match_card, format_profile_card

logger = get_logger("telegram-decorators")


def send_telegram_message(chat_id: int | str, text: str) -> bool:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set in environment. Skipping Telegram dispatch.")
        return False

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
            return True
        else:
            logger.error(
                f"Failed to send Telegram message to chat_id={chat_id}: "
                f"status={resp.status_code}, response={resp.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Exception sending Telegram message to chat_id={chat_id}: {e}")
        return False


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
            matches = []
            if isinstance(result, list):
                matches = result
            elif isinstance(result, dict) and "matches" in result:
                matches = result["matches"]
            elif isinstance(result, dict) and "match" in result:
                matches = [result["match"]]

            # If result only returned match_id (e.g. {"status": "completed", "match_id": 10})
            if not matches:
                match_id = None
                if isinstance(result, dict) and "match_id" in result:
                    match_id = result["match_id"]
                elif "body" in kwargs and hasattr(kwargs["body"], "match_id"):
                    match_id = kwargs["body"].match_id

                if match_id:
                    from api.config import get_database_url
                    from core.infrastructure.db.pipeline_repository import PipelineJobRepository

                    repo = PipelineJobRepository(get_database_url())
                    unnotified = repo.matches.get_unnotified_matches(limit=20)
                    matches = [m for m in unnotified if m.get("match_id") == int(match_id)]

            for m in matches:
                if not isinstance(m, dict):
                    continue
                chat_id = m.get("telegram_chat_id")
                if not chat_id:
                    continue

                msg = format_match_card(m)
                if send_telegram_message(chat_id, msg):
                    if "match_id" in m:
                        from api.config import get_database_url
                        from core.infrastructure.db.pipeline_repository import PipelineJobRepository

                        repo = PipelineJobRepository(get_database_url())
                        repo.matches.mark_as_notified([m["match_id"]])
        except Exception as e:
            logger.error(f"Error in notify_telegram_on_matches_found decorator: {e}")

        return result

    return wrapper
