from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.services.providers.base import LLMProvider

logger = logging.getLogger(__name__)


def get_provider(provider_id: str, settings: Settings | None = None) -> LLMProvider:
    settings = settings or Settings.from_env()
    if provider_id == "openai":
        from app.services.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)
    if provider_id == "gigachat":
        from app.services.providers.gigachat_provider import GigaChatProvider

        return GigaChatProvider(settings)
    raise ValueError(f"Unknown LLM provider: {provider_id}")
