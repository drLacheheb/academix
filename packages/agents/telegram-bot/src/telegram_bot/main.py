import os
import sys

from core.infrastructure.logging.logger import get_logger
from core.utils.agent import get_agent_name
from core.utils.api import make_api_client
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_bot.edit_handler import get_edit_handler
from telegram_bot.handlers import (
    delete_callback_handler,
    delete_command,
    handle_document,
    help_command,
    matches_command,
    profile_command,
    start_command,
    status_command,
    upload_cv_command,
)

load_dotenv()


async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot & view instructions"),
        BotCommand("upload_cv", "Upload a new or updated CV document"),
        BotCommand("status", "Track your CV pipeline processing progress"),
        BotCommand("profile", "View your parsed skills, degree & interests"),
        BotCommand("edit", "Edit profile skills, degree, or locations"),
        BotCommand("matches", "Browse your top academic job matches"),
        BotCommand("delete", "Permanently delete your profile & CV for a fresh start"),
        BotCommand("help", "Show available commands & guide"),
    ]
    await application.bot.set_my_commands(commands)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = get_logger("telegram-bot-error-handler")
    logger.error(f"Uncaught Telegram exception: {context.error}", exc_info=context.error)


def run():
    agent_name = get_agent_name("telegram-bot-worker")
    logger = get_logger(agent_name)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN environment variable is not set! "
            "Please create a bot with @BotFather and set TELEGRAM_BOT_TOKEN in .env"
        )
        sys.exit(1)

    logger.info(f"Starting Multi-User Telegram Bot Agent (name: {agent_name})")

    api = make_api_client(timeout=30.0)

    try:
        from telegram.request import HTTPXRequest

        req = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0)
        app = ApplicationBuilder().token(token).request(req).post_init(post_init).build()
        app.bot_data["api"] = api
        app.add_error_handler(global_error_handler)

        # Register Command Handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("profile", profile_command))
        app.add_handler(CommandHandler("matches", matches_command))
        app.add_handler(CommandHandler(["upload_cv", "uploadcv", "newcv"], upload_cv_command))
        app.add_handler(CommandHandler(["delete", "reset", "deleteprofile"], delete_command))

        # Register Callback Handlers
        app.add_handler(CallbackQueryHandler(delete_callback_handler, pattern="^delete_"))

        # Register Edit Conversation Handler
        app.add_handler(get_edit_handler())

        # Register PDF Document Upload Handler
        app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        # Background notification jobs are registered in post_init above

        webhook_host = os.environ.get("WEBHOOK_HOST", "academix-telegram-bot.azurecontainerapps.io")
        port = int(os.environ.get("PORT", "8080"))
        secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")

        webhook_url = f"https://{webhook_host}/telegram/webhook"
        logger.info(f"Starting Telegram Bot in WEBHOOK mode at {webhook_url} (port {port})")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/telegram/webhook",
            webhook_url=webhook_url,
            secret_token=secret_token,
            drop_pending_updates=True,
        )
    except Exception as e:
        logger.error(f"Fatal error in Telegram Bot agent: {e}")
        raise
    finally:
        api.close()


if __name__ == "__main__":
    run()
