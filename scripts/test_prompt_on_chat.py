#!/usr/bin/env python3
"""Transcribe an audio chat and audit it with two prompt versions side-by-side."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.core.config import Settings
from app.services.providers.factory import get_provider
from app.services.transcription import TranscriptionService
from app.utils.text import strip_markdown_fence

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SYSTEM_PROMPT = (
    "Ты проводишь аудит диалога по строгим правилам из архитектурного документа. "
    "Следуй правилам точно и не добавляй лишних пояснений."
)


def run_audit(transcript: str, prompt_text: str, settings: Settings | None = None) -> dict:
    settings = settings or Settings.from_env()
    provider = get_provider("openai", settings)
    config = load_runtime_config(settings)
    model = str(config.get("openai_model", "gpt-4.1-mini"))
    provider_cfg = config.get("providers", {}).get("openai", {})
    temperature = float(provider_cfg.get("temperature", 0.1))
    max_tokens = int(provider_cfg.get("max_tokens", 2048))

    user_prompt = (
        f"{prompt_text}\n\n"
        "Ниже транскрипт для аудита.\n"
        "<transcript>\n"
        f"{transcript}\n"
        "</transcript>"
    )

    response = provider.chat_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return {
        "analysis": strip_markdown_fence(response["content"]),
        "model": model,
        "tokens": response.get("usage"),
    }


def load_runtime_config(settings: Settings) -> dict:
    path = settings.storage_dir / "config.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path, help="Path to MP3/WAV chat recording")
    parser.add_argument("baseline_prompt", type=Path, help="Path to baseline prompt markdown")
    parser.add_argument("improved_prompt", type=Path, help="Path to improved prompt markdown")
    parser.add_argument("output_dir", type=Path, help="Directory to save transcript and analyses")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()

    logger.info("Transcribing %s ...", args.audio)
    transcript = TranscriptionService(settings).transcribe(args.audio)
    transcript_path = args.output_dir / "transcript.txt"
    transcript_path.write_text(transcript, encoding="utf-8")
    logger.info("Transcript saved to %s (%d chars)", transcript_path, len(transcript))

    baseline_text = args.baseline_prompt.read_text(encoding="utf-8")
    improved_text = args.improved_prompt.read_text(encoding="utf-8")

    logger.info("Running baseline prompt...")
    baseline_result = run_audit(transcript, baseline_text, settings)
    (args.output_dir / "analysis-baseline.md").write_text(baseline_result["analysis"], encoding="utf-8")
    logger.info("Baseline tokens: %s", baseline_result["tokens"])

    logger.info("Running improved prompt...")
    improved_result = run_audit(transcript, improved_text, settings)
    (args.output_dir / "analysis-improved.md").write_text(improved_result["analysis"], encoding="utf-8")
    logger.info("Improved tokens: %s", improved_result["tokens"])

    logger.info("Done. Results in %s", args.output_dir)


if __name__ == "__main__":
    main()
