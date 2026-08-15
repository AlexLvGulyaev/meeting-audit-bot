from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    assemblyai_api_key: str
    openai_api_key: str
    gigachat_auth_key: str | None
    gigachat_base_url: str
    gigachat_token_url: str
    gigachat_scope: str
    gigachat_ca_bundle: str | None
    database_url: str
    admin_token: str
    admin_demo_token: str
    admin_user_id: int | None
    log_level: str
    storage_dir: Path
    storage_uploads_dir: Path
    storage_prompts_dir: Path
    storage_transcripts_dir: Path
    storage_audits_dir: Path
    prompts_dir: Path
    app_host: str
    app_port: int

    @classmethod
    def from_env(cls) -> "Settings":
        admin_user_id_raw = os.getenv("ADMIN_USER_ID", "").strip()
        admin_user_id = int(admin_user_id_raw) if admin_user_id_raw.isdigit() else None

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            assemblyai_api_key=os.getenv("ASSEMBLYAI_API_KEY", "").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            gigachat_auth_key=os.getenv("GIGACHAT_AUTH_KEY", "").strip() or None,
            gigachat_base_url=os.getenv(
                "GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1"
            ).strip(),
            gigachat_token_url=os.getenv(
                "GIGACHAT_TOKEN_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            ).strip(),
            gigachat_scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS").strip(),
            gigachat_ca_bundle=os.getenv("GIGACHAT_CA_BUNDLE", "").strip() or None,
            database_url=os.getenv("DATABASE_URL", "").strip(),
            admin_token=os.getenv("ADMIN_TOKEN", "").strip(),
            admin_demo_token=os.getenv("ADMIN_DEMO_TOKEN", "").strip(),
            admin_user_id=admin_user_id,
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            storage_dir=BASE_DIR / "storage",
            storage_uploads_dir=BASE_DIR / "storage" / "uploads",
            storage_prompts_dir=BASE_DIR / "storage" / "prompts",
            storage_transcripts_dir=BASE_DIR / "storage" / "transcripts",
            storage_audits_dir=BASE_DIR / "storage" / "audits",
            prompts_dir=BASE_DIR / "prompts",
            app_host=os.getenv("APP_HOST", "0.0.0.0").strip(),
            app_port=int(os.getenv("APP_PORT", "8000").strip()),
        )
