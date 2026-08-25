from unittest.mock import AsyncMock, MagicMock

from telegram_bot.edit_handler import (
    CHOOSING_FIELD,
    TYPING_VALUE,
    cancel_edit,
    edit_start,
    field_chosen,
    get_edit_handler,
    value_received,
)
from telegram_bot.main import global_error_handler


async def test_edit_start_success():
    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query = None
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 200
    api_mock.get.return_value.json.return_value = [
        {"id": 1, "name": "Curie", "skills": ["Physics"]}
    ]
    context.bot_data = {"api": api_mock}

    state = await edit_start(update, context)
    assert state == CHOOSING_FIELD
    update.message.reply_text.assert_awaited_once()
    assert context.user_data["editing_profile_id"] == 1


async def test_edit_start_no_profile():
    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query = None
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 404
    api_mock.get.return_value.json.return_value = []
    context.bot_data = {"api": api_mock}

    state = await edit_start(update, context)
    assert state == -1  # ConversationHandler.END


async def test_field_chosen_skills():
    update = MagicMock()
    update.callback_query.data = "field_skills"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {
        "current_profile": {"skills": ["Physics", "Chemistry"]}
    }

    state = await field_chosen(update, context)
    assert state == TYPING_VALUE
    assert context.user_data["editing_field"] == "skills"
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "Editing Skills" in update.callback_query.edit_message_text.call_args[0][0]


async def test_field_chosen_cancel():
    update = MagicMock()
    update.callback_query.data = "cancel_edit"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}

    state = await field_chosen(update, context)
    assert state == -1  # ConversationHandler.END
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "Profile editing cancelled" in update.callback_query.edit_message_text.call_args[0][0]


async def test_value_received_success():
    update = MagicMock()
    update.message.text = "Robotics, Autonomous Systems"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {
        "editing_field": "skills",
        "editing_profile_id": 1,
        "editing_label": "Skills (comma-separated)",
    }
    api_mock = MagicMock()
    patch_resp = MagicMock()
    patch_resp.status_code = 200
    api_mock.patch.return_value = patch_resp
    context.bot_data = {"api": api_mock}

    state = await value_received(update, context)
    assert state == -1  # ConversationHandler.END
    api_mock.patch.assert_called_once_with(
        "/profiles/1", json={"skills": ["Robotics", "Autonomous Systems"]}
    )
    update.message.reply_text.assert_awaited_once()
    assert "Updated Successfully" in update.message.reply_text.call_args[0][0]


async def test_cancel_edit_command():
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    state = await cancel_edit(update, context)
    assert state == -1
    update.message.reply_text.assert_awaited_once()
    assert "cancelled" in update.message.reply_text.call_args[0][0]


def test_get_edit_handler():
    handler = get_edit_handler()
    assert handler is not None
    assert len(handler.entry_points) == 2


async def test_global_error_handler():
    context = MagicMock()
    context.error = ValueError("Test error")
    await global_error_handler(None, context)


async def test_edit_start_api_error():
    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query = None
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}
    api_mock = MagicMock()
    api_mock.get.side_effect = Exception("Service unavailable")
    context.bot_data = {"api": api_mock}

    state = await edit_start(update, context)
    assert state == -1
    update.message.reply_text.assert_awaited_once()
    assert "Failed to load profile" in update.message.reply_text.call_args[0][0]


async def test_field_chosen_invalid_choice():
    update = MagicMock()
    update.callback_query.data = "invalid_field_random"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}

    state = await field_chosen(update, context)
    assert state == -1
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "Invalid selection" in update.callback_query.edit_message_text.call_args[0][0]


async def test_value_received_session_expired():
    update = MagicMock()
    update.message.text = "New Value"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}  # missing editing_field / profile_id
    context.bot_data = {"api": MagicMock()}

    state = await value_received(update, context)
    assert state == -1
    update.message.reply_text.assert_awaited_once()
    assert "Session expired" in update.message.reply_text.call_args[0][0]


async def test_value_received_api_patch_error():
    update = MagicMock()
    update.message.text = "Dr. Marie Curie"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {
        "editing_field": "name",
        "editing_profile_id": 1,
        "editing_label": "Full Name",
    }
    api_mock = MagicMock()
    api_mock.patch.side_effect = Exception("API 500 error")
    context.bot_data = {"api": api_mock}

    state = await value_received(update, context)
    assert state == -1
    update.message.reply_text.assert_awaited_once()
    assert "Failed to update profile" in update.message.reply_text.call_args[0][0]

