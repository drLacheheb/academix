import html

from core.infrastructure.logging.logger import get_logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = get_logger("telegram-bot-edit")

CHOOSING_FIELD = 0
TYPING_VALUE = 1


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_chat or context.user_data is None:
        return ConversationHandler.END

    chat_id = str(update.effective_chat.id)
    api = context.bot_data.get("api")
    if not api:
        msg = "API service unavailable."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    try:
        if update.callback_query:
            await update.callback_query.answer()

        resp = api.get(f"/profiles/by-chat-id/{chat_id}")
        if resp.status_code != 200 or not resp.json():
            msg = "No CV profile found to edit. Please upload your CV PDF first."
            if update.callback_query:
                await update.callback_query.edit_message_text(msg)
            elif update.message:
                await update.message.reply_text(msg)
            return ConversationHandler.END

        profiles = resp.json()
        profile = profiles[0]
        context.user_data["editing_profile_id"] = profile["id"]
        context.user_data["current_profile"] = profile

        keyboard = [
            [
                InlineKeyboardButton("Skills", callback_data="field_skills"),
                InlineKeyboardButton(
                    "Research Interests", callback_data="field_research_interests"
                ),
            ],
            [
                InlineKeyboardButton("Highest Degree", callback_data="field_highest_degree"),
                InlineKeyboardButton("Degree Fields", callback_data="field_degree_fields"),
            ],
            [
                InlineKeyboardButton(
                    "Preferred Locations", callback_data="field_preferred_locations"
                ),
                InlineKeyboardButton("Full Name", callback_data="field_name"),
            ],
            [
                InlineKeyboardButton("Cancel", callback_data="cancel_edit"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        prompt = "<b>Select which profile field you want to edit:</b>"

        if update.callback_query:
            await update.callback_query.edit_message_text(
                prompt, reply_markup=reply_markup, parse_mode="HTML"
            )
        elif update.message:
            await update.message.reply_text(
                prompt, reply_markup=reply_markup, parse_mode="HTML"
            )
        return CHOOSING_FIELD

    except Exception as e:
        logger.error(f"Error starting edit for {chat_id}: {e}")
        msg = "Failed to load profile for editing."
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return ConversationHandler.END


async def field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or context.user_data is None:
        return ConversationHandler.END

    await query.answer()

    if query.data == "cancel_edit":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ]
            ]
        )
        await query.edit_message_text("Profile editing cancelled.", reply_markup=keyboard)
        return ConversationHandler.END

    field_map = {
        "field_skills": ("skills", "Skills (comma-separated)"),
        "field_research_interests": (
            "research_interests",
            "Research Interests (comma-separated)",
        ),
        "field_highest_degree": (
            "highest_degree",
            "Highest Degree (e.g. Master, PhD, Postdoc)",
        ),
        "field_degree_fields": (
            "degree_fields",
            "Degree Fields (comma-separated, e.g. Computer Science, Molecular Biology)",
        ),
        "field_preferred_locations": (
            "preferred_locations",
            "Preferred Locations (comma-separated, e.g. Netherlands, Germany)",
        ),
        "field_name": ("name", "Full Name"),
    }

    choice = field_map.get(query.data or "")
    if not choice:
        await query.edit_message_text("Invalid selection.")
        return ConversationHandler.END

    field_key, field_label = choice
    context.user_data["editing_field"] = field_key
    context.user_data["editing_label"] = field_label

    profile = context.user_data.get("current_profile", {})
    curr_val = profile.get(field_key) if profile else None
    if isinstance(curr_val, list):
        curr_str = ", ".join(curr_val) if curr_val else "None"
    else:
        curr_str = str(curr_val) if curr_val else "None"

    prompt_msg = (
        f"<b>Editing {field_label}</b>\n\n"
        f"<b>Current Value:</b>\n<code>{html.escape(curr_str)}</code>\n\n"
        "<i>Please type your updated value in a message below (or type /cancel to abort):</i>"
    )
    await query.edit_message_text(prompt_msg, parse_mode="HTML")
    return TYPING_VALUE


async def value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text or context.user_data is None:
        return TYPING_VALUE

    text = update.message.text.strip()
    field_key = context.user_data.get("editing_field")
    profile_id = context.user_data.get("editing_profile_id")
    api = context.bot_data.get("api")

    if not field_key or not profile_id or not api:
        await update.message.reply_text("Session expired. Please start over with /edit.")
        return ConversationHandler.END

    # Process value
    if field_key in ("skills", "research_interests", "preferred_locations", "degree_fields"):
        new_val = [item.strip() for item in text.split(",") if item.strip()]
    else:
        new_val = text

    try:
        patch_resp = api.patch(f"/profiles/{profile_id}", json={field_key: new_val})
        patch_resp.raise_for_status()

        label = context.user_data.get("editing_label", field_key)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ],
                [
                    InlineKeyboardButton("Edit Another Field", callback_data="nav_edit"),
                ],
            ]
        )
        await update.message.reply_text(
            f"<b>{label} Updated Successfully.</b>\n\n"
            "Re-matching has been enqueued against all academic vacancies.\n"
            "You will be notified automatically when new matching results are ready.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        logger.info(f"Updated profile {profile_id} field {field_key} via Telegram edit")

    except Exception as e:
        logger.error(f"Error patching profile {profile_id}: {e}")
        await update.message.reply_text("Failed to update profile. Please try again.")

    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("My Profile", callback_data="nav_profile"),
                    InlineKeyboardButton("Browse Matches", callback_data="nav_matches"),
                ]
            ]
        )
        await update.message.reply_text("Profile edit cancelled.", reply_markup=keyboard)
    return ConversationHandler.END


def get_edit_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("edit", edit_start),
            CallbackQueryHandler(edit_start, pattern="^nav_edit$"),
        ],
        states={
            CHOOSING_FIELD: [CallbackQueryHandler(field_chosen)],
            TYPING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, value_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
        per_message=False,
    )
