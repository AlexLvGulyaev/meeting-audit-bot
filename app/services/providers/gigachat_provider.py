from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.services.providers.base import LLMProvider

logger = logging.getLogger(__name__)

try:
    from app.services.providers.gigachat_adapter import GigaChatAdapter, GigaChatError
except ImportError:
    GigaChatAdapter = None  # type: ignore[assignment, misc]
    GigaChatError = RuntimeError  # type: ignore[assignment, misc]


class GigaChatProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._adapter: Any = None

    def _get_adapter(self):
        if self._adapter is None:
            if GigaChatAdapter is None:
                raise RuntimeError(
                    "GigaChat-адаптер не импортирован. Проверьте PYTHONPATH или скопируйте gigachat_adapter.py."
                )
            self._adapter = GigaChatAdapter(
                base_url=self.settings.gigachat_base_url,
                token_url=self.settings.gigachat_token_url,
                scope=self.settings.gigachat_scope,
                auth_key=self.settings.gigachat_auth_key,
                ca_bundle=self.settings.gigachat_ca_bundle,
            )
        return self._adapter

    def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        adapter = self._get_adapter()
        response = adapter.chat_completions(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.get("content", "")
        if not content:
            raise RuntimeError("GigaChat returned empty analysis.")
        return content.strip()

    def test_connection(self) -> bool:
        try:
            self.chat_completion(
                system_prompt="You are a test assistant.",
                user_prompt="Say OK.",
                model=self.settings.gigachat_model,
                temperature=0.0,
                max_tokens=5,
            )
            return True
        except Exception as exc:
            logger.warning("GigaChat connection test failed: %s", exc)
            return False
