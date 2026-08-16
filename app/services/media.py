from __future__ import annotations

import asyncio
import logging
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from telegram import Message

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediaFile:
    file_id: str
    file_unique_id: str
    filename: str
    mime_type: str
    duration: int | None


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\-]", "_", name.strip()) or "upload"


def extract_media_file_data(message: Message) -> Optional[MediaFile]:
    if message.video:
        mime = message.video.mime_type or "video/mp4"
        extension = mimetypes.guess_extension(mime) or ".mp4"
        filename = f"{message.video.file_unique_id}{extension}"
        return MediaFile(
            file_id=message.video.file_id,
            file_unique_id=message.video.file_unique_id,
            filename=filename,
            mime_type=mime,
            duration=message.video.duration,
        )

    if message.document and (message.document.mime_type or "").startswith("video/"):
        original_name = message.document.file_name or ""
        extension = Path(original_name).suffix or mimetypes.guess_extension(
            message.document.mime_type or ""
        ) or ".mp4"
        safe_name = _safe_name(Path(original_name).name) if original_name else ""
        filename = safe_name or f"{message.document.file_unique_id}{extension}"
        return MediaFile(
            file_id=message.document.file_id,
            file_unique_id=message.document.file_unique_id,
            filename=filename,
            mime_type=message.document.mime_type or "video/mp4",
            duration=None,
        )

    if message.audio:
        mime = message.audio.mime_type or "audio/mpeg"
        original_name = message.audio.file_name or ""
        extension = Path(original_name).suffix or mimetypes.guess_extension(mime) or ".mp3"
        safe_name = _safe_name(original_name) if original_name else ""
        filename = safe_name or f"{message.audio.file_unique_id}{extension}"
        return MediaFile(
            file_id=message.audio.file_id,
            file_unique_id=message.audio.file_unique_id,
            filename=filename,
            mime_type=mime,
            duration=message.audio.duration,
        )

    if message.document and (message.document.mime_type or "").startswith("audio/"):
        original_name = message.document.file_name or ""
        extension = Path(original_name).suffix or mimetypes.guess_extension(
            message.document.mime_type or ""
        ) or ".mp3"
        safe_name = _safe_name(original_name) if original_name else ""
        filename = safe_name or f"{message.document.file_unique_id}{extension}"
        return MediaFile(
            file_id=message.document.file_id,
            file_unique_id=message.document.file_unique_id,
            filename=filename,
            mime_type=message.document.mime_type or "audio/mpeg",
            duration=None,
        )

    if message.video_note:
        filename = f"{message.video_note.file_unique_id}.mp4"
        return MediaFile(
            file_id=message.video_note.file_id,
            file_unique_id=message.video_note.file_unique_id,
            filename=filename,
            mime_type="video/mp4",
            duration=message.video_note.duration,
        )

    if message.voice:
        filename = f"{message.voice.file_unique_id}.ogg"
        return MediaFile(
            file_id=message.voice.file_id,
            file_unique_id=message.voice.file_unique_id,
            filename=filename,
            mime_type="audio/ogg",
            duration=message.voice.duration,
        )

    return None


async def download_media(
    bot,
    media: MediaFile,
    destination: Path,
) -> None:
    telegram_file = await bot.get_file(media.file_id)
    await telegram_file.download_to_drive(custom_path=str(destination))
