from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from app.core.config import Settings

logger = logging.getLogger(__name__)

ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"


class AssemblyAIError(RuntimeError):
    """Raised when AssemblyAI returns an error state."""


class TranscriptionService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    def _headers(self) -> dict[str, str]:
        return {"authorization": self.settings.assemblyai_api_key}

    def upload(self, file_path: Path) -> str:
        with file_path.open("rb") as audio_file:
            response = requests.post(
                ASSEMBLYAI_UPLOAD_URL,
                headers=self._headers(),
                data=audio_file,
                timeout=1200,
            )
        response.raise_for_status()
        upload_url = response.json().get("upload_url")
        if not upload_url:
            raise AssemblyAIError("AssemblyAI did not return upload_url.")
        return upload_url

    def create_transcript(self, upload_url: str) -> str:
        response = requests.post(
            ASSEMBLYAI_TRANSCRIPT_URL,
            headers={**self._headers(), "content-type": "application/json"},
            json={
                "audio_url": upload_url,
                "speech_models": ["universal-3-5-pro"],
                "speaker_labels": True,
            },
            timeout=60,
        )
        response.raise_for_status()
        transcript_id = response.json().get("id")
        if not transcript_id:
            raise AssemblyAIError("AssemblyAI did not return transcript id.")
        return transcript_id

    def poll_transcript(self, transcript_id: str, timeout_seconds: int = 3600) -> dict:
        endpoint = f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}"
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(endpoint, headers=self._headers(), timeout=60)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status == "completed":
                return payload
            if status == "error":
                raise AssemblyAIError(payload.get("error") or "Unknown AssemblyAI error.")
            time.sleep(3)
        raise TimeoutError("Timed out while waiting for AssemblyAI transcription.")

    def _format_utterances(self, payload: dict) -> str:
        utterances = payload.get("utterances") or []
        if not utterances:
            text = (payload.get("text") or "").strip()
            return text
        lines: list[str] = []
        for u in utterances:
            speaker = u.get("speaker", "Unknown")
            text = (u.get("text") or "").strip()
            if text:
                lines.append(f"Speaker {speaker}: {text}")
        return "\n".join(lines)

    def transcribe(self, file_path: Path) -> str:
        upload_url = self.upload(file_path)
        transcript_id = self.create_transcript(upload_url)
        payload = self.poll_transcript(transcript_id)
        transcript = self._format_utterances(payload)
        if not transcript:
            raise AssemblyAIError("AssemblyAI returned empty transcript.")
        logger.info("Transcription completed: %s chars, %s utterances", len(transcript), len(payload.get("utterances") or []))
        return transcript
