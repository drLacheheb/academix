import asyncio
import os
import sys
from contextlib import asynccontextmanager

from core.infrastructure.logging.logger import get_logger
from core.utils.api import make_api_client
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from uvicorn import run as uvicorn_run

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

bot_app = None


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
    asyncio.create_task(application.bot.set_my_commands(commands))


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = get_logger("telegram-bot-error-handler")
    logger.error(f"Uncaught Telegram exception: {context.error}", exc_info=context.error)


@asynccontextmanager
async def lifespan(app_fastapi: FastAPI):
    global bot_app
    logger = get_logger("telegram-bot-webhook")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        sys.exit(1)

    api = make_api_client(timeout=30.0)
    bot_app = ApplicationBuilder().token(token).post_init(post_init).build()
    bot_app.bot_data["api"] = api
    bot_app.add_error_handler(global_error_handler)

    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("status", status_command))
    bot_app.add_handler(CommandHandler("profile", profile_command))
    bot_app.add_handler(CommandHandler("matches", matches_command))
    bot_app.add_handler(CommandHandler(["upload_cv", "uploadcv", "newcv"], upload_cv_command))
    bot_app.add_handler(CommandHandler(["delete", "reset", "deleteprofile"], delete_command))
    bot_app.add_handler(CallbackQueryHandler(delete_callback_handler, pattern="^delete_"))
    bot_app.add_handler(get_edit_handler())
    bot_app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    await bot_app.initialize()
    await bot_app.start()

    webhook_host = os.environ.get("WEBHOOK_HOST", "localhost:8000")
    secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")
    scheme = "https" if "localhost" not in webhook_host else "http"
    webhook_url = f"{scheme}://{webhook_host}/telegram/webhook"

    logger.info(f"Setting Telegram Webhook URL in background: {webhook_url}")
    asyncio.create_task(
        bot_app.bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token,
            drop_pending_updates=True,
        )
    )

    yield

    await bot_app.stop()
    await bot_app.shutdown()
    api.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")
    if secret_token and x_telegram_bot_api_secret_token != secret_token:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Secret Token")

    if bot_app is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: Bot not initialized")

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    asyncio.create_task(bot_app.process_update(update))
    return {"status": "ok"}


def run():
    port = int(os.environ.get("PORT", "8080"))
    uvicorn_run("telegram_bot.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
