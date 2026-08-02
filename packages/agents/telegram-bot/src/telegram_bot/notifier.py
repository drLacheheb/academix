import asyncio
import html
from datetime import timedelta

from core.infrastructure.logging.logger import get_logger
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import ContextTypes

logger = get_logger("telegram-bot-notifier")


async def check_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.bot_data.get("api")
    if not api:
        return

    try:
        resp = api.get("/matches/unnotified?limit=20")
        if resp.status_code != 200:
            logger.error(f"Failed to fetch unnotified matches: {resp.status_code}")
            return

        unnotified_matches = resp.json()
        if not unnotified_matches:
            return

        sent_ids: list[int] = []
        for m in unnotified_matches:
            chat_id = m.get("telegram_chat_id")
            match_id = m.get("match_id")
            if not chat_id or not match_id:
                continue

            score = m.get("score", 0.0)
            percentage = int(score * 100)
            title = html.escape(m.get("job_title", "Academic Position"))
            employer = html.escape(m.get("employer") or "Academic Institution")
            location = html.escape(m.get("location") or "")
            deadline = html.escape(m.get("deadline") or "Not specified")
            explanation = html.escape(m.get("explanation") or "Matching requirements satisfied.")
            job_url = m.get("job_url", "")

            location_str = f" ({location})" if location else ""
            msg = (
                f"🎯 <b>New Match Found! ({percentage}% Match)</b>\n\n"
                f"📌 <b>{title}</b>\n"
                f"🏛️ {employer}{location_str}\n"
                f"⏰ Deadline: {deadline}\n\n"
                f"💡 <i>{explanation}</i>\n\n"
                f"🔗 <a href='{job_url}'>View Job Posting</a>"
            )

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode="HTML",
                )
                sent_ids.append(match_id)
                logger.info(f"Sent Telegram notification for match {match_id} to chat_id {chat_id}")
                await asyncio.sleep(0.05)  # Telegram API rate limit protection
            except Forbidden:
                logger.warning(
                    f"User {chat_id} has blocked the bot or chat was deleted. Skipping..."
                )
                sent_ids.append(match_id)  # Mark as notified so we don't retry endlessly
            except RetryAfter as e:
                raw_delay = e.retry_after
                if isinstance(raw_delay, timedelta):
                    delay = raw_delay.total_seconds()
                else:
                    delay = float(raw_delay)
                logger.warning(f"Telegram Rate Limit hit (RetryAfter {delay}s). Pausing...")
                await asyncio.sleep(delay)
            except TelegramError as e:
                logger.error(f"Telegram API error sending to {chat_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending to {chat_id}: {e}")

        if sent_ids:
            mark_resp = api.put("/matches/mark-notified", json={"match_ids": sent_ids})
            mark_resp.raise_for_status()
            logger.info(f"Marked {len(sent_ids)} matches as notified.")

    except Exception as e:
        logger.error(f"Error in Telegram match notification cycle: {e}")

    try:
        await check_profile_notifications(context)
    except Exception as e:
        logger.error(f"Error in profile notification execution: {e}")


async def check_profile_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    api = context.bot_data.get("api")
    if not api:
        return

    try:
        resp = api.get("/profiles/unnotified-completed?limit=10")
        if resp.status_code != 200 or not resp.json():
            return

        unnotified_profiles = resp.json()
        sent_ids: list[int] = []

        from telegram_bot.handlers import format_profile_card

        for p in unnotified_profiles:
            chat_id = p.get("telegram_chat_id")
            prof_id = p.get("id")
            if not chat_id or not prof_id:
                continue

            card_body = format_profile_card(p)
            header = f"🎉 <b>CV Processing Complete! (Profile #{prof_id})</b>\n\n"
            full_msg = f"{header}{card_body}"

            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=full_msg,
                    parse_mode="HTML",
                )
                sent_ids.append(prof_id)
                logger.info(
                    f"Sent profile completion notification for profile #{prof_id} "
                    f"to chat_id {chat_id}"
                )
                await asyncio.sleep(0.05)
            except Forbidden:
                logger.warning(
                    f"User {chat_id} blocked bot. Marking profile #{prof_id} as notified..."
                )
                sent_ids.append(prof_id)
            except Exception as e:
                logger.error(f"Error sending profile notification to {chat_id}: {e}")

        if sent_ids:
            mark_resp = api.put("/profiles/mark-notified", json={"profile_ids": sent_ids})
            mark_resp.raise_for_status()
            logger.info(f"Marked {len(sent_ids)} candidate profiles as notified.")

    except Exception as e:
        logger.error(f"Error in profile notification cycle: {e}")

