#!/usr/bin/env python3
"""Generate a mono MP3 from a client chat text using two OpenAI TTS voices."""

from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

from pydub import AudioSegment

from app.core.config import Settings

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment, misc]


VOICES = {
    "Клиент": "nova",
    "Менеджер": "echo",
}
DEFAULT_MODEL = "tts-1"


def parse_chat(text: str) -> list[tuple[str, str]]:
    """Parse lines like 'Клиент: ...' or 'Менеджер: ...'."""
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^(Клиент|Менеджер):\s*(.*)$", line)
        if match:
            speaker, content = match.groups()
            lines.append((speaker, content))
    return lines


def tts_to_segment(text: str, voice: str, client: OpenAI, model: str = DEFAULT_MODEL) -> AudioSegment:
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
        tmp_path = Path(fp.name)
    response.stream_to_file(tmp_path)
    segment = AudioSegment.from_mp3(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return segment


def build_mono_mp3(
    turns: list[tuple[str, str]],
    output_path: Path,
    client: OpenAI,
    pause_ms: int = 800,
) -> None:
    """Build mono MP3 alternating two OpenAI TTS voices."""
    result = AudioSegment.silent(duration=0)
    pause = AudioSegment.silent(duration=pause_ms)

    for speaker, content in turns:
        voice = VOICES.get(speaker, "alloy")
        segment = tts_to_segment(content, voice, client)
        segment = segment.normalize()
        result = result + segment + pause

    result.export(output_path, format="mp3", bitrate="192k")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert client chat to mono MP3 using OpenAI TTS")
    parser.add_argument("input", type=Path, help="Path to chat markdown file")
    parser.add_argument("output", type=Path, help="Path to output MP3")
    args = parser.parse_args()

    if OpenAI is None:
        raise RuntimeError("Python-пакет `openai` не установлен.")

    settings = Settings.from_env()
    client = OpenAI(api_key=settings.openai_api_key)

    chat_text = args.input.read_text(encoding="utf-8")
    turns = parse_chat(chat_text)
    if not turns:
        raise ValueError("No dialog lines found. Expected format: 'Клиент: ...' or 'Менеджер: ...'")

    build_mono_mp3(turns, args.output, client)
    print(f"Generated {args.output} with {len(turns)} turns")


if __name__ == "__main__":
    main()
