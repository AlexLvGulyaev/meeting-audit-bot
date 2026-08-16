from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import Settings
from app.core.runtime_config import RuntimeConfig
from app.services.audit import AuditService
from app.services.execution import ExecutionService
from app.services.media import extract_media_file_data, download_media
from app.services.prompt_loader import PromptLoader
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

MESSAGE_CHUNK_SIZE = 3900
MAX_UPLOADS_PER_DAY = 5


class TelegramBot:
    def __init__(
        self,
        settings: Settings | None = None,
        storage: StorageService | None = None,
        audit: AuditService | None = None,
        execution: ExecutionService | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.storage = storage or StorageService(self.settings)
        self.audit = audit or AuditService(self.settings)
        self.execution = execution or ExecutionService(self.settings)

    def _split_for_telegram(self, text: str) -> list[str]:
        if len(text) <= MESSAGE_CHUNK_SIZE:
            return [text]
        chunks: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= MESSAGE_CHUNK_SIZE:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, MESSAGE_CHUNK_SIZE)
            if split_at == -1:
                split_at = MESSAGE_CHUNK_SIZE
            chunks.append(remaining[:split_at].rstrip())
            remaining = remaining[split_at:].lstrip()
        return chunks

    def build_application(self) -> Application:
        app = Application.builder().token(self.settings.telegram_bot_token).build()
        app.bot_data["bot_instance"] = self

        app.add_handler(CommandHandler("start", self.start_handler))
        app.add_handler(CommandHandler("help", self.help_handler))
        app.add_handler(
            MessageHandler(
                filters.VIDEO
                | filters.Document.VIDEO
                | filters.AUDIO
                | filters.Document.AUDIO,
                self.handle_media,
            )
        )
        app.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_unsupported)
        )
        return app

    def _available_scenarios_text(self) -> str:
        """Возвращает markdown-описание доступных сценариев и активного промпта."""
        try:
            runtime_cfg = RuntimeConfig(self.settings).load()
            active_prompt_id = runtime_cfg.get("prompt_id", "onboarding")
            loader = PromptLoader(self.settings)
            prompts = loader.list_prompts()
        except Exception:
            return ""

        lines: list[str] = []
        lines.append("*Доступные сценарии аудита:*")
        for prompt in prompts:
            marker = "✅" if prompt["id"] == active_prompt_id else "•"
            lines.append(f"{marker} *{prompt['name']}* — `/{prompt['id']}`")
        lines.append("")
        lines.append(f"*Сейчас активен:* `{active_prompt_id}`")
        lines.append("Администратор может сменить сценарий в /admin.")
        return "\n".join(lines)

    async def start_handler(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        scenarios = self._available_scenarios_text()
        text = (
            "Привет! Я аудитор встреч и звонков.\n\n"
            "Отправьте видео или mp3-файл, и я сделаю транскрипт через AssemblyAI "
            "с разделением по спикерам, затем проверю диалог по активному сценарию.\n\n"
        )
        if scenarios:
            text += scenarios
        await update.message.reply_text(text, parse_mode="Markdown")

    async def help_handler(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        scenarios = self._available_scenarios_text()
        text = (
            "*Как использовать:*\n"
            "1) Отправьте видео или mp3.\n"
            "2) Дождитесь транскрибации и анализа.\n"
            "3) Получите готовый аудит в чате.\n\n"
            "*Поддерживаемые форматы:* mp3, mp4, ogg, wav, m4a и другие, которые Telegram распознаёт как аудио/видео.\n\n"
        )
        if scenarios:
            text += scenarios
        else:
            text += "Список сценариев временно недоступен."
        await update.message.reply_text(text, parse_mode="Markdown")

    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        message = update.message
        media = extract_media_file_data(message)
        if not media:
            await message.reply_text("Не вижу подходящего файла. Отправьте видео или mp3.")
            return

        user_id = message.from_user.id if message.from_user else None
        username = message.from_user.username if message.from_user else None

        if user_id != self.settings.admin_user_id:
            used = self.storage.count_uploads_today(user_id)
            if used >= MAX_UPLOADS_PER_DAY:
                await message.reply_text(
                    f"Лимит обработок на сегодня исчерпан ({MAX_UPLOADS_PER_DAY}). "
                    "Попробуйте завтра."
                )
                return

        progress = await message.reply_text("Файл получен. Скачиваю...")
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

        session_id = self.execution.start_session(
            chat_id=message.chat_id,
            user_id=user_id,
            username=username,
            file_id=media.file_id,
            filename=media.filename,
        )

        transcript: str | None = None
        analysis_result: dict | None = None
        status = "failed"
        error_message: str | None = None
        upload_path: Path | None = None
        transcript_path: Path | None = None
        audit_path: Path | None = None
        storage_filename: str | None = None

        try:
            self.execution.start_step(session_id, "download")
            tmp_dir_path = Path(tempfile.mkdtemp(prefix="tg_meeting_audit_"))
            upload_path = tmp_dir_path / media.filename
            await download_media(context.bot, media, upload_path)
            # Сохраняем оригинал, загруженный из Telegram, в persistent-хранилище.
            # filename остаётся человекочитаемым; storage_filename — уникальное имя файла на диске.
            safe_name = Path(media.filename).name
            storage_filename = f"{session_id}_{safe_name}"
            storage_path = self.settings.storage_uploads_dir / storage_filename
            shutil.copy(upload_path, storage_path)
            self.execution.finish_step(session_id, "download", status="ok", metadata={"size_bytes": upload_path.stat().st_size})

            self.execution.start_step(session_id, "transcribe")
            transcript = await asyncio.to_thread(self._transcribe, upload_path)
            self.execution.finish_step(
                session_id, "transcribe", status="ok",
                metadata={"chars": len(transcript)}
            )

            self.execution.start_step(session_id, "audit")
            analysis_result = await asyncio.to_thread(self.audit.analyze, transcript)
            analysis = analysis_result["analysis"]
            provider = analysis_result["provider"]
            prompt_id = analysis_result["prompt_id"]
            model = analysis_result.get("model")
            self.execution.finish_step(
                session_id, "audit", status="ok",
                metadata={
                    "provider": provider,
                    "model": model,
                    "prompt_id": prompt_id,
                    "chars": len(analysis),
                    "tokens_in": analysis_result.get("tokens_in"),
                    "tokens_out": analysis_result.get("tokens_out"),
                    "tokens_total": analysis_result.get("tokens_total"),
                }
            )
            status = "success"

            self.execution.start_step(session_id, "persist")
            audit_record = self.storage.save_audit(
                chat_id=message.chat_id,
                user_id=user_id,
                username=username,
                file_id=media.file_id,
                file_unique_id=media.file_unique_id,
                filename=media.filename,
                transcript=transcript,
                analysis=analysis,
                status=status,
                error_message=None,
                provider=provider,
                prompt_id=prompt_id,
                mime_type=media.mime_type,
                file_size=upload_path.stat().st_size,
                duration=media.duration,
                storage_filename=storage_filename,
            )
            self.execution.finish_step(session_id, "persist", status="ok", metadata={"audit_id": audit_record})
            self.storage.update_execution_session_video_audit_id(session_id, audit_record)
            self.storage.update_execution_session_storage_filename(session_id, storage_filename)
            self.execution.finish_session(session_id, status="success")

            await progress.edit_text("Анализ готов. Отправляю результат...")
            for chunk in self._split_for_telegram(analysis):
                await message.reply_text(chunk)
            await progress.delete()

        except Exception as exc:
            logger.exception("Failed to process media: %s", exc)
            error_message = str(exc)
            try:
                self.execution.finish_step(session_id, "audit", status="error", metadata={"error": error_message})
            except Exception:
                pass
            try:
                self.execution.finish_session(session_id, status="failed")
            except Exception:
                pass
            try:
                audit_record = self.storage.save_audit(
                    chat_id=message.chat_id,
                    user_id=user_id,
                    username=username,
                    file_id=media.file_id,
                    file_unique_id=media.file_unique_id,
                    filename=media.filename,
                    transcript=transcript,
                    analysis=analysis_result.get("analysis") if analysis_result else None,
                    status="failed",
                    error_message=error_message,
                    provider=analysis_result.get("provider") if analysis_result else None,
                    prompt_id=analysis_result.get("prompt_id") if analysis_result else None,
                    mime_type=media.mime_type,
                    file_size=upload_path.stat().st_size if upload_path else None,
                    duration=media.duration,
                    storage_filename=storage_filename,
                )
                if storage_filename:
                    try:
                        self.storage.update_execution_session_storage_filename(session_id, storage_filename)
                    except Exception:
                        pass
                if audit_record:
                    try:
                        self.storage.update_execution_session_video_audit_id(session_id, audit_record)
                    except Exception:
                        pass
            except Exception:
                logger.exception("Failed to save failed audit")
            await progress.edit_text(
                "Не получилось обработать файл. Проверьте ключи и попробуйте снова."
            )

    def _transcribe(self, local_path: Path) -> str:
        from app.services.transcription import TranscriptionService

        return TranscriptionService(self.settings).transcribe(local_path)

    async def handle_unsupported(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            "Отправьте видео или mp3, чтобы я запустил анализ. "
            "Список сценариев и активный промпт — в /help или /start."
        )
