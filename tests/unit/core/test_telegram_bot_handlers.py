from telegram_bot.handlers import render_match_page


def test_render_match_page_empty():
    text, keyboard = render_match_page([], 0)
    assert "No matches found yet" in text
    assert len(keyboard.inline_keyboard) > 0


def test_render_match_page_single():
    matches = [
        {
            "score": 0.95,
            "job_title": "PhD Position in Robotics",
            "employer": "ETH Zurich",
            "city": "Zurich",
            "country": "Switzerland",
            "deadline": "2026-10-15",
            "job_degree_fields": ["Robotics", "Computer Science"],
            "explanation": "Direct match on robotics background.",
            "job_url": "https://example.com/robotics-phd",
        }
    ]
    text, keyboard = render_match_page(matches, 0)
    assert "Match 1 of 1 (95% Match)" in text
    assert "PhD Position in Robotics" in text

    # Navigation row has 1 row with Prev, 1 / 1, Next
    nav_row = keyboard.inline_keyboard[0]
    assert len(nav_row) == 3
    assert nav_row[1].text == "1 / 1"

    # URL button row
    url_row = keyboard.inline_keyboard[1]
    assert url_row[0].url == "https://example.com/robotics-phd"


def test_render_match_page_multiple_pagination():
    matches = [
        {
            "score": 0.9,
            "job_title": f"Job {i}",
            "employer": "Uni",
            "deadline": "2026-10-01",
            "job_url": f"https://example.com/job/{i}",
        }
        for i in range(1, 4)
    ]
    # Page 0 (First page)
    text0, kb0 = render_match_page(matches, 0)
    assert "Match 1 of 3 (90% Match)" in text0
    nav0 = kb0.inline_keyboard[0]
    assert nav0[0].callback_data == "noop"
    assert nav0[2].callback_data == "match_page_1"

    # Page 1 (Middle page)
    text1, kb1 = render_match_page(matches, 1)
    assert "Match 2 of 3 (90% Match)" in text1
    nav1 = kb1.inline_keyboard[0]
    assert nav1[0].callback_data == "match_page_0"
    assert nav1[2].callback_data == "match_page_2"

    # Page 2 (Last page)
    text2, kb2 = render_match_page(matches, 2)
    assert "Match 3 of 3 (90% Match)" in text2
    nav2 = kb2.inline_keyboard[0]
    assert nav2[0].callback_data == "match_page_1"
    assert nav2[2].callback_data == "noop"


async def test_post_init_syncs_metadata():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.main import post_init

    app_mock = MagicMock()
    app_mock.bot.set_my_commands = AsyncMock()
    app_mock.bot.set_my_description = AsyncMock()
    app_mock.bot.set_my_short_description = AsyncMock()
    app_mock.bot.set_chat_menu_button = AsyncMock()

    await post_init(app_mock)

    app_mock.bot.set_my_commands.assert_awaited_once()
    app_mock.bot.set_my_description.assert_awaited_once()
    app_mock.bot.set_my_short_description.assert_awaited_once()
    app_mock.bot.set_chat_menu_button.assert_awaited_once()


async def test_start_command_new_user():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import start_command

    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_user.first_name = "Marie"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 404
    api_mock.get.return_value.json.return_value = []
    context.bot_data = {"api": api_mock}

    await start_command(update, context)

    update.message.reply_text.assert_awaited_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "Welcome <b>Marie</b> to Academix" in call_args


async def test_start_command_returning_user():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import start_command

    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_user.first_name = "Marie"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 200
    api_mock.get.return_value.json.return_value = [{"id": 1, "name": "Marie"}]
    context.bot_data = {"api": api_mock}

    await start_command(update, context)

async def test_help_command_message():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import help_command

    update = MagicMock()
    update.callback_query = None
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await help_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Academix Assistant - Command Guide" in update.message.reply_text.call_args[0][0]


async def test_help_command_callback():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import help_command

    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.message = None
    context = MagicMock()

    await help_command(update, context)
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_text.assert_awaited_once()


async def test_status_command_with_profile():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import status_command

    update = MagicMock()
    update.callback_query = None
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 200
    api_mock.get.return_value.json.return_value = [
        {
            "cv_file_path": "uploads/cv_marie.pdf",
            "status": "COMPLETED",
            "status_message": "All done",
        }
    ]
    context.bot_data = {"api": api_mock}

    await status_command(update, context)
    update.message.reply_text.assert_awaited_once()
    call_text = update.message.reply_text.call_args[0][0]
    assert "cv_marie.pdf" in call_text
    assert "100%" in call_text


async def test_status_command_no_profile():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import status_command

    update = MagicMock()
    update.callback_query = None
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 404
    api_mock.get.return_value.json.return_value = []
    context.bot_data = {"api": api_mock}

    await status_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "No active CV profile found" in update.message.reply_text.call_args[0][0]


async def test_profile_command_success():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import profile_command

    update = MagicMock()
    update.callback_query = None
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    api_mock = MagicMock()
    api_mock.get.return_value.status_code = 200
    api_mock.get.return_value.json.return_value = [
        {
            "id": 1,
            "name": "Dr. Marie Curie",
            "highest_degree": "PhD",
            "skills": ["Radioactivity", "Physics"],
        }
    ]
    context.bot_data = {"api": api_mock}

    await profile_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Dr. Marie Curie" in update.message.reply_text.call_args[0][0]


async def test_matches_command_with_results():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import matches_command

    update = MagicMock()
    update.callback_query = None
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.user_data = {}
    context.bot.send_chat_action = AsyncMock()
    api_mock = MagicMock()
    # /profiles/by-chat-id
    prof_resp = MagicMock()
    prof_resp.status_code = 200
    prof_resp.json.return_value = [{"id": 42}]
    # /profiles/42/matches
    match_resp = MagicMock()
    match_resp.status_code = 200
    match_resp.json.return_value = {
        "matches": [
            {
                "score": 0.88,
                "job_title": "Postdoc in Physics",
                "employer": "Sorbonne",
                "job_url": "https://example.com/sorbonne",
            }
        ]
    }
    api_mock.get.side_effect = [prof_resp, match_resp]
    context.bot_data = {"api": api_mock}

    await matches_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Postdoc in Physics" in update.message.reply_text.call_args[0][0]
    assert context.user_data["cached_matches"] is not None


async def test_upload_cv_command():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import upload_cv_command

    update = MagicMock()
    update.callback_query = None
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await upload_cv_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Upload Your CV" in update.message.reply_text.call_args[0][0]


async def test_handle_document_invalid_extension():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import handle_document

    update = MagicMock()
    update.message.document.file_name = "cv.docx"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await handle_document(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Unsupported file format" in update.message.reply_text.call_args[0][0]


async def test_handle_document_valid_pdf_success():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import handle_document

    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_user.full_name = "Marie Curie"
    update.message.document.file_name = "marie_curie_cv.pdf"
    update.message.document.file_id = "doc_123"
    update.message.reply_text = AsyncMock()

    tg_file_mock = MagicMock()
    tg_file_mock.download_as_bytearray = AsyncMock(return_value=b"%PDF-1.4 mock content")

    context = MagicMock()
    context.bot.get_file = AsyncMock(return_value=tg_file_mock)
    context.bot.send_chat_action = AsyncMock()

    api_mock = MagicMock()
    upload_resp = MagicMock()
    upload_resp.status_code = 200
    upload_resp.json.return_value = {"id": 99}
    api_mock.post.return_value = upload_resp
    context.bot_data = {"api": api_mock}

    await handle_document(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "CV Uploaded Successfully" in update.message.reply_text.call_args[0][0]
    assert "#99" in update.message.reply_text.call_args[0][0]


async def test_delete_command_prompt():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import delete_command

    update = MagicMock()
    update.callback_query = None
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await delete_command(update, context)
    update.message.reply_text.assert_awaited_once()
    assert "Are you sure you want to delete" in update.message.reply_text.call_args[0][0]


async def test_delete_callback_cancel():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import delete_callback_handler

    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query.data = "delete_cancel"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = MagicMock()

    await delete_callback_handler(update, context)
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "Deletion Cancelled" in update.callback_query.edit_message_text.call_args[0][0]


async def test_delete_callback_confirm_success():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import delete_callback_handler

    update = MagicMock()
    update.effective_chat.id = 12345
    update.callback_query.data = "delete_confirm"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    api_mock = MagicMock()
    del_resp = MagicMock()
    del_resp.status_code = 200
    api_mock.delete.return_value = del_resp
    context.bot_data = {"api": api_mock}

    await delete_callback_handler(update, context)
    update.callback_query.edit_message_text.assert_awaited_once()
    assert "Profile deleted." in update.callback_query.edit_message_text.call_args[0][0]


async def test_navigation_callback_handler_routing():
    from unittest.mock import AsyncMock, MagicMock

    from telegram_bot.handlers import navigation_callback_handler

    # Test noop
    update = MagicMock()
    update.callback_query.data = "noop"
    update.callback_query.answer = AsyncMock()
    context = MagicMock()

    await navigation_callback_handler(update, context)
    update.callback_query.answer.assert_awaited_once()

    # Test match_page_1 with cached matches
    update2 = MagicMock()
    update2.callback_query.data = "match_page_1"
    update2.callback_query.answer = AsyncMock()
    update2.callback_query.edit_message_text = AsyncMock()
    context2 = MagicMock()
    context2.user_data = {
        "cached_matches": [
            {"job_title": "Job 1", "score": 0.9, "employer": "U1"},
            {"job_title": "Job 2", "score": 0.85, "employer": "U2"},
        ]
    }

    await navigation_callback_handler(update2, context2)
    update2.callback_query.edit_message_text.assert_awaited_once()
    assert "Job 2" in update2.callback_query.edit_message_text.call_args[0][0]



