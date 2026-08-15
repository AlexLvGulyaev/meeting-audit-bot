from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application

from app.core.config import Settings
from app.core.default_config import DEFAULT_CONFIG
from app.core.logging_config import configure_logging
from app.core.runtime_config import RuntimeConfig
from app.routes import admin, health
from app.services.prompt_loader import PromptLoader
from app.services.storage import StorageService
from app.services.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)


def _seed_runtime_config() -> None:
    runtime = RuntimeConfig()
    cfg = runtime.load()
    # Merge missing default keys without overwriting existing values.
    merged: dict = DEFAULT_CONFIG.copy()
    merged.update(cfg)
    runtime.save(merged)
    logger.info("Runtime config loaded/seeded: %s", merged.get("prompt_id"))


def _ensure_storage_paths(settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    for path in [
        settings.storage_uploads_dir,
        settings.storage_prompts_dir,
        settings.storage_transcripts_dir,
        settings.storage_audits_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    logger.info("Storage directories ready: %s", settings.storage_uploads_dir)


def _ensure_prompts() -> None:
    loader = PromptLoader()
    for prompt_id in loader.list_prompts():
        logger.info("Prompt available: %s (%s)", prompt_id["id"], prompt_id["source"])


async def _start_telegram_polling(app: FastAPI) -> None:
    bot = TelegramBot()
    telegram_app = bot.build_application()
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    app.state.telegram_app = telegram_app
    app.state.telegram_bot = bot
    logger.info("Telegram polling started")


async def _stop_telegram_polling(app: FastAPI) -> None:
    telegram_app: Application | None = getattr(app.state, "telegram_app", None)
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        logger.info("Telegram polling stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(Settings.from_env())
    _ensure_storage_paths()
    _seed_runtime_config()
    _ensure_prompts()

    storage = StorageService()
    storage.init_tables_with_retry()
    logger.info("Database tables initialized")

    await _start_telegram_polling(app)
    logger.info("Application startup complete")

    yield

    await _stop_telegram_polling(app)
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Meeting Audit Bot",
        description="Telegram bot for STT + LLM audit of meetings and sales calls.",
        version="1.0.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.include_router(health.router)
    app.include_router(admin.router)

    return app


app = create_app()
