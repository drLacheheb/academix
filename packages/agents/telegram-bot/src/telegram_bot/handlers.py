import html
import io

from core.infrastructure.logging.logger import get_logger
from core.utils.decorators import unblock_chat
from core.utils.formatters import (
    format_profile_card,
    format_single_match_card,
    format_status_bar,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

logger = get_logger("telegram-bot-handlers")


def render_match_page(matches: list[dict], page: int) -> tuple[str, InlineKeyboardMarkup]:
    total = len(matches)
    if total == 0:
        text = "No matches found yet. We are actively crawling and matching vacancies for you."
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Pipeline Status", callback_data="nav_status")],
                [InlineKeyboardButton("My Profile", callback_data="nav_profile")],
            ]
        )
        return text, keyboard

    page = max(0, min(page, total - 1))
    m = matches[page]
    card_text = format_single_match_card(m, page + 1, total)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("< Prev", callback_data=f"match_page_{page - 1}"))
    else:
        nav_row.append(InlineKeyboardButton("< Prev", callback_data="noop"))

    nav_row.append(InlineKeyboardButton(f"{page + 1} / {total}", callback_data="noop"))

    if page < total - 1:
        nav_row.append(InlineKeyboardButton("Next >", callback_data=f"match_page_{page + 1}"))
    else:
        nav_row.append(InlineKeyboardButton("Next >", callback_data="noop"))

    keyboard_rows = [
        nav_row,
    ]
    job_url = m.get("job_url")
    if job_url:
        keyboard_rows.append([InlineKeyboardButton("Open Vacancy Posting", url=job_url)])
    keyboard_rows.append(
        [
            InlineKeyboardButton("My Profile", callback_data="nav_profile"),
            InlineKeyboardButton("Pipeline Status", callback_data="nav_status"),
        ]
    )
    return card_text, InlineKeyboardMarkup(keyboard_rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    user_name = update.effective_user.first_name if update.effective_user else "Researcher"
    chat_id = str(update.effective_chat.id)
    unblock_chat(chat_id)

    # Support deep-linking payloads (e.g., https://t.me/AcadamixBot?start=matches)
    if context.args:
        payload = context.args[0].lower().strip()
        if payload in ("matches", "match"):
            await matches_command(update, context)
            return
        if payload in ("profile", "cv"):
            await profile_command(update, context)
            return
        if payload in ("status", "pipeline"):
            await status_command(update, context)
            return
        if payload in ("upload", "upload_cv", "newcv"):
            await upload_cv_command(update, context)
            return
        if payload in ("help", "guide"):
            await help_command(update, context)
            return

    # Detect returning users for idempotent /start
    api = context.bot_data.get("api")
    is_returning = False
    if api:
        try:
            resp = api.get(f"/profiles/by-chat-id/{chat_id}")
            if resp.status_code == 200 and resp.json():
                is_returning = True
        except Exception as e:
            logger.debug(f"Could not verify returning profile for chat_id {chat_id}: {e}")

    if is_returning:
        welcome_text = f"Welcome back, <b>{html.escape(user_name)}</b>."
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                ],
                [
                    InlineKeyboardButton("Pipeline Status", callback_data="nav_status"),
                    InlineKeyboardButton("Upload New CV", callback_data="nav_upload"),
                ],
            ]
        )
    else:
        welcome_text = (
            f"Welcome <b>{html.escape(user_name)}</b> to Academix.\n\n"
            "AI-powered academic job matching. Send your CV as a PDF "
            "or press /start to open the menu."
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Upload CV", callback_data="nav_upload"),
                    InlineKeyboardButton("Help and Guide", callback_data="nav_help"),
                ],
            ]
        )

    await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "<b>Academix Assistant - Command Guide</b>\n\n"
        "<b>/upload_cv</b> - Upload a CV PDF document\n"
        "<b>/status</b> - Track CV processing progress\n"
        "<b>/profile</b> - View extracted skills, degree, and domains\n"
        "<b>/edit</b> - Edit skills, degree fields, or preferred locations\n"
        "<b>/matches</b> - Browse matched academic positions\n"
        "<b>/delete</b> - Reset and delete all profile data\n"
        "<b>/help</b> - Show this guide"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Upload CV", callback_data="nav_upload"),
                InlineKeyboardButton("Pipeline Status", callback_data="nav_status"),
            ],
            [
                InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
            ],
        ]
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            help_text, parse_mode="HTML", reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=keyboard)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    if not update.callback_query:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Could not send typing action for chat_id {chat_id}: {e}")
    api = context.bot_data.get("api")
    if not api:
        msg = "API service unavailable."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Upload CV", callback_data="nav_upload")]]
            )
            msg = "No active CV profile found. Please send your CV as a PDF file to get started."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    msg, parse_mode="HTML", reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
            return

        profiles = resp.json()[:5]
        status_lines = ["<b>Your CV Processing Status:</b>\n"]

        for idx, p in enumerate(profiles, start=1):
            filename = html.escape(p.get("cv_file_path") or "cv.pdf").split("/")[-1].split("\\")[-1]
            status = p.get("status", "UNKNOWN")
            msg = p.get("status_message") or ""
            progress_bar = format_status_bar(status)

            status_lines.append(
                f"<b>Profile #{idx}</b> (<i>{filename}</i>)\n"
                f"{progress_bar}\n"
                f"Detail: {html.escape(msg)}\n"
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Refresh Status", callback_data="refresh_status"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ],
                [
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                ],
            ]
        )
        full_text = "\n".join(status_lines)

        if update.callback_query:
            await update.callback_query.answer("Status refreshed.")
            await update.callback_query.edit_message_text(
                full_text, parse_mode="HTML", reply_markup=keyboard
            )
        elif update.message:
            await update.message.reply_text(full_text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error fetching status for chat_id {chat_id}: {e}")
        err_msg = "Failed to retrieve profile status. Please try again."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(err_msg)
        elif update.message:
            await update.message.reply_text(err_msg)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    if not update.callback_query:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Could not send typing action for chat_id {chat_id}: {e}")
    api = context.bot_data.get("api")
    if not api:
        msg = "API service unavailable."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Upload CV", callback_data="nav_upload")]]
            )
            msg = "No CV profile found. Upload your CV PDF first."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    msg, parse_mode="HTML", reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
            return

        profiles = resp.json()
        p = profiles[0]
        profile_text = format_profile_card(p)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Edit Profile", callback_data="nav_edit"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ],
                [
                    InlineKeyboardButton("Delete Profile", callback_data="delete_confirm_prompt"),
                ],
            ]
        )

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                profile_text, parse_mode="HTML", reply_markup=keyboard
            )
        elif update.message:
            await update.message.reply_text(profile_text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in profile command for {chat_id}: {e}")
        err_msg = "Failed to load profile details."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(err_msg)
        elif update.message:
            await update.message.reply_text(err_msg)


async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    if not update.callback_query:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Could not send typing action for chat_id {chat_id}: {e}")
    api = context.bot_data.get("api")
    if not api:
        msg = "API service unavailable."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return

    try:
        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Upload CV", callback_data="nav_upload")]]
            )
            msg = "Please upload a CV first to get matched jobs."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    msg, parse_mode="HTML", reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
            return

        profiles = resp.json()
        p = profiles[0]
        profile_id = p["id"]

        matches_resp = api.get(f"/profiles/{profile_id}/matches?limit=20")
        if matches_resp.status_code != 200 or not matches_resp.json().get("matches"):
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Pipeline Status", callback_data="nav_status")],
                    [InlineKeyboardButton("My Profile", callback_data="nav_profile")],
                ]
            )
            msg = "No matches found yet. We are actively crawling and matching vacancies for you."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    msg, parse_mode="HTML", reply_markup=keyboard
                )
            elif update.message:
                await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
            return

        matches = matches_resp.json()["matches"]
        if context.user_data is not None:
            context.user_data["cached_matches"] = matches

        card_text, keyboard = render_match_page(matches, 0)

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                card_text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
            )
        elif update.message:
            await update.message.reply_text(
                card_text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
            )

    except Exception as e:
        logger.error(f"Error fetching matches for {chat_id}: {e}")
        err_msg = "Failed to fetch matches."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(err_msg)
        elif update.message:
            await update.message.reply_text(err_msg)


async def upload_cv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = (
        "<b>Upload Your CV</b>\n\n"
        "Send your CV as a <b>PDF file</b> in this chat, or press /start to return to the menu.\n"
        "The AI pipeline will extract your skills, degree, and research domains automatically."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(prompt, parse_mode="HTML")
    elif update.message:
        await update.message.reply_text(prompt, parse_mode="HTML")


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

    if isinstance(doc.file_size, int):
        if doc.file_size == 0:
            await update.message.reply_text(
                "The uploaded file is empty. Please upload a valid PDF CV."
            )
            return
        if doc.file_size > 20 * 1024 * 1024:
            await update.message.reply_text(
                "The file exceeds the 20MB size limit. Please upload a smaller file."
            )
            return

    chat_id = str(update.effective_chat.id)
    user_name = update.effective_user.full_name if update.effective_user else None

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

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

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Check Pipeline Status", callback_data="nav_status"),
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                ]
            ]
        )
        await update.message.reply_text(
            f"<b>CV Uploaded Successfully.</b> (Profile ID: #{prof_id})\n\n"
            "The AI pipeline is extracting, translating, and matching your profile.\n"
            "Use the button below to track progress or wait for instant match alerts.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        logger.info(f"Registered CV upload from Telegram user {chat_id} (profile #{prof_id})")

    except Exception as e:
        logger.error(f"Error handling CV document from Telegram {chat_id}: {e}")
        await update.message.reply_text(
            "Failed to process your CV. Please make sure it is a valid PDF and try again."
        )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Yes, Delete Everything", callback_data="delete_confirm"),
                InlineKeyboardButton("Cancel", callback_data="delete_cancel"),
            ]
        ]
    )
    msg = (
        "<b>Are you sure you want to delete your profile?</b>\n\n"
        "This action will permanently remove:\n"
        "- Your candidate profile & CV document\n"
        "- Your extracted skills & vector embeddings\n"
        "- All calculated job matches & notification history\n\n"
        "<i>This action cannot be undone.</i>"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)


async def delete_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message or not update.effective_chat:
        return

    await query.answer()
    chat_id = str(update.effective_chat.id)

    if query.data == "delete_cancel":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ]
            ]
        )
        await query.edit_message_text(
            "<b>Deletion Cancelled.</b> Your profile and CV remain safe.",
            parse_mode="HTML",
            reply_markup=keyboard,
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

            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Upload New CV", callback_data="nav_upload")]]
            )
            await query.edit_message_text(
                "<b>Profile deleted.</b> Upload a new CV to start fresh.",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info(f"Successfully deleted all profile data for Telegram user {chat_id}")
        except Exception as e:
            logger.error(f"Failed to delete profile for Telegram user {chat_id}: {e}")
            await query.edit_message_text(
                "Failed to delete your profile data. Please try again later."
            )


async def navigation_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_chat:
        return

    data = query.data

    if data == "noop":
        await query.answer(text="")
        return

    if data in ("refresh_status", "nav_status"):
        await status_command(update, context)
        return

    if data == "nav_profile":
        await profile_command(update, context)
        return

    if data == "nav_matches":
        await matches_command(update, context)
        return

    if data == "nav_upload":
        await upload_cv_command(update, context)
        return

    if data == "nav_help":
        await help_command(update, context)
        return

    if data == "delete_confirm_prompt":
        await delete_command(update, context)
        return

    if data.startswith("match_page_"):
        await query.answer()
        try:
            page = int(data.split("_")[-1])
        except ValueError:
            page = 0

        matches = context.user_data.get("cached_matches") if context.user_data else None
        if not matches:
            chat_id = str(update.effective_chat.id)
            api = context.bot_data.get("api")
            if api:
                resp = api.get(f"/profiles/by-chat-id/{chat_id}")
                if resp.status_code == 200 and resp.json():
                    prof_id = resp.json()[0]["id"]
                    matches_resp = api.get(f"/profiles/{prof_id}/matches?limit=20")
                    if matches_resp.status_code == 200:
                        matches = matches_resp.json().get("matches", [])
                        if context.user_data is not None:
                            context.user_data["cached_matches"] = matches

        if not matches:
            await query.edit_message_text(
                "No matches cached. Use /matches to refresh.", parse_mode="HTML"
            )
            return

        card_text, keyboard = render_match_page(matches, page)
        await query.edit_message_text(
            card_text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
        )
