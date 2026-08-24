import html
import io
import json

from core.infrastructure.logging.logger import get_logger
from core.utils.formatters import format_profile_card
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

logger = get_logger("telegram-bot-handlers")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name if update.effective_user else "Researcher"
    welcome_text = (
        f"Welcome <b>{html.escape(user_name)}</b> to Academic Career Engine!\n\n"
        "I am your personal AI research career assistant.\n\n"
        "<b>Available Commands:</b>\n"
        "<b>/upload_cv</b> - Upload your CV (PDF document)\n"
        "<b>/status</b> - Check your CV processing pipeline status\n"
        "<b>/profile</b> - View your parsed skills, degree & research interests\n"
        "<b>/edit</b> - Edit profile skills, degree, or locations\n"
        "<b>/matches</b> - View your top academic job matches\n"
        "<b>/help</b> - Show command guide"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "<b>Available Commands:</b>\n\n"
        "<b>/upload_cv</b> (or /uploadcv) - Prompt to upload a CV document\n"
        "<b>/status</b> - View pipeline stage for your uploaded CVs\n"
        "<b>/profile</b> - See your parsed skills, research interests, and degree\n"
        "<b>/edit</b> - Edit skills, research interests, degree, or locations\n"
        "<b>/matches</b> - View your top matched academic vacancies\n"
        "<b>/help</b> - Show this help message"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="HTML")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    chat_id = str(update.effective_chat.id)
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass
    api = context.bot_data.get("api")
    if not api:
        await update.message.reply_text("API service unavailable.")
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            await update.message.reply_text(
                "No active CV profile found. Please send your CV as a PDF file to get started!"
            )
            return

        profiles = resp.json()
        status_lines = ["<b>Your CV Processing Status:</b>\n"]

        status_map = {
            "INGESTING": "Ingesting CV...",
            "PENDING_DETECTION": "Language Detection...",
            "DETECTION_CLAIMED": "Detecting Language...",
            "PENDING_TRANSLATION": "Translating Profile...",
            "TRANSLATION_CLAIMED": "Translating Profile...",
            "PENDING_REFINEMENT": "Structuring Profile...",
            "REFINEMENT_CLAIMED": "Structuring Profile...",
            "PENDING_EMBEDDING": "Generating Vector Embeddings...",
            "EMBEDDING_CLAIMED": "Generating Vector Embeddings...",
            "COMPLETED": "Ready & Matched!",
            "FAILED": "Processing Failed",
        }

        for idx, p in enumerate(profiles, start=1):
            filename = html.escape(p.get("cv_file_path") or "cv.pdf").split("/")[-1].split("\\")[-1]
            status = p.get("status", "UNKNOWN")
            msg = p.get("status_message") or ""
            badge = status_map.get(status, status)

            status_lines.append(
                f"<b>Profile #{idx}</b> (<i>{filename}</i>)\n"
                f"Status: {badge}\n"
                f"Detail: {html.escape(msg)}\n"
            )

        await update.message.reply_text("\n".join(status_lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error fetching status for chat_id {chat_id}: {e}")
        await update.message.reply_text("Failed to retrieve profile status. Please try again.")


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    chat_id = str(update.effective_chat.id)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    api = context.bot_data.get("api")
    if not api:
        await update.message.reply_text("API service unavailable.")
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            await update.message.reply_text("No CV profile found. Upload your CV PDF first!")
            return

        profiles = resp.json()
        p = profiles[0]
        profile_text = format_profile_card(p)
        await update.message.reply_text(profile_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in profile command for {chat_id}: {e}")
        await update.message.reply_text("Failed to load profile details.")


async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    chat_id = str(update.effective_chat.id)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    api = context.bot_data.get("api")
    if not api:
        await update.message.reply_text("API service unavailable.")
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            await update.message.reply_text("Please upload a CV first to get matched jobs!")
            return

        profiles = resp.json()
        p = profiles[0]
        profile_id = p["id"]

        matches_resp = api.get(f"/profiles/{profile_id}/matches?limit=5")
        if matches_resp.status_code != 200 or not matches_resp.json().get("matches"):
            await update.message.reply_text(
                "No matches found yet. We are actively crawling & matching vacancies for you!"
            )
            return

        matches = matches_resp.json()["matches"]
        msg_lines = ["<b>Top Vacancy Matches for You:</b>\n"]

        for idx, m in enumerate(matches, start=1):
            score_pct = int(m.get("score", 0.0) * 100)
            url = m.get("job_url", "")
            title = html.escape(m.get("job_title") or "Academic Position")
            employer = html.escape(m.get("employer") or "Academic Institution")
            location = html.escape(m.get("location") or "")
            deadline = html.escape(m.get("deadline") or "Not specified")
            explanation = html.escape(m.get("explanation") or "Matching criteria satisfied.")
            raw_degrees = m.get("job_degree_fields") or m.get("degree_fields") or []
            if isinstance(raw_degrees, str):
                try:
                    parsed = json.loads(raw_degrees)
                    degree_fields = parsed if isinstance(parsed, list) else [raw_degrees]
                except Exception:
                    degree_fields = [raw_degrees]
            elif isinstance(raw_degrees, list):
                degree_fields = raw_degrees
            else:
                degree_fields = []

            location_str = f" ({location})" if location else ""
            degree_str = (
                f"\nDegree: {html.escape(', '.join(str(d) for d in degree_fields))}"
                if degree_fields
                else ""
            )

            msg_lines.append(
                f"<b>{idx}. {title} ({score_pct}% Match)</b>\n"
                f"{employer}{location_str}\n"
                f"Deadline: {deadline}{degree_str}\n"
                f"<i>{explanation}</i>\n"
                f"<a href='{url}'>Open Vacancy Posting</a>\n"
            )

        await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error fetching matches for {chat_id}: {e}")
        await update.message.reply_text("Failed to fetch matches.")


async def upload_cv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Please send your CV as a <b>PDF document</b> in this chat.",
            parse_mode="HTML",
        )


async def newcv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await upload_cv_command(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document or not update.effective_chat:
        return

    doc = update.message.document
    file_name = doc.file_name or "cv.pdf"

    if not file_name.lower().endswith(".pdf"):
        await update.message.reply_text("Unsupported file format. Please upload a PDF file (.pdf).")
        return

    chat_id = str(update.effective_chat.id)
    user_name = update.effective_user.full_name if update.effective_user else None

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
    await update.message.reply_text("Receiving your CV... Uploading to pipeline...")

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = await tg_file.download_as_bytearray()

        api = context.bot_data.get("api")
        if not api:
            await update.message.reply_text("API service unavailable. Try again later.")
            return

        files = {"file": (file_name, io.BytesIO(file_bytes), "application/pdf")}
        data = {"telegram_chat_id": chat_id, "name": user_name}

        upload_resp = api.post("/profiles/upload-cv", data=data, files=files)
        upload_resp.raise_for_status()

        profile_data = upload_resp.json()
        prof_id = profile_data.get("id")

        await update.message.reply_text(
            f"<b>CV Uploaded Successfully!</b> (Profile ID: #{prof_id})\n\n"
            "The AI pipeline is now extracting, translating, and matching your profile.\n"
            "Use <b>/status</b> anytime to view progress, or wait for instant match alerts!",
            parse_mode="HTML",
        )
        logger.info(f"Registered CV upload from Telegram user {chat_id} (profile #{prof_id})")

    except Exception as e:
        logger.error(f"Error handling CV document from Telegram {chat_id}: {e}")
        await update.message.reply_text(
            "Failed to process your CV. Please make sure it is a valid PDF and try again."
        )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Yes, Delete Everything", callback_data="delete_confirm"),
                InlineKeyboardButton("Cancel", callback_data="delete_cancel"),
            ]
        ]
    )

    await update.message.reply_text(
        "<b>Are you sure you want to delete your profile?</b>\n\n"
        "This action will permanently remove:\n"
        "• Your candidate profile & CV document\n"
        "• Your extracted skills & vector embeddings\n"
        "• All calculated job matches & notification history\n\n"
        "<i>This action cannot be undone.</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def delete_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message or not update.effective_chat:
        return

    await query.answer()
    chat_id = str(update.effective_chat.id)

    if query.data == "delete_cancel":
        await query.edit_message_text(
            "<b>Deletion Cancelled.</b> Your profile and CV remain safe.",
            parse_mode="HTML",
        )
        return

    if query.data == "delete_confirm":
        api = context.bot_data.get("api")
        if not api:
            await query.edit_message_text("API service unavailable. Try again later.")
            return

        try:
            del_resp = api.delete(f"/profiles/by-telegram-chat-id/{chat_id}")
            if del_resp.status_code == 404:
                await query.edit_message_text("No active profile found to delete.")
                return
            del_resp.raise_for_status()

            await query.edit_message_text(
                "<b>Your profile and CV data have been permanently deleted.</b>\n\n"
                "You now have a clean start. You can upload a new CV anytime by sending a PDF file "
                "or using <b>/upload_cv</b>.",
                parse_mode="HTML",
            )
            logger.info(f"Successfully deleted all profile data for Telegram user {chat_id}")
        except Exception as e:
            logger.error(f"Failed to delete profile for Telegram user {chat_id}: {e}")
            await query.edit_message_text(
                "Failed to delete your profile data. Please try again later."
            )
