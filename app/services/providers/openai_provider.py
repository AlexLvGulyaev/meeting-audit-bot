from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.providers.base import LLMProvider

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment, misc]


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._client: Any = None

    def _get_client(self, base_url: str | None = None):
        if self._client is None:
            kwargs = {"api_key": self.settings.openai_api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if OpenAI is None:
            raise RuntimeError("Python-пакет `openai` не установлен.")
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        result = content.strip() if isinstance(content, str) else str(content).strip()
        if not result:
            raise RuntimeError("OpenAI returned empty analysis.")
        usage = None
        try:
            if response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(response.usage, "completion_tokens", None),
                    "total_tokens": getattr(response.usage, "total_tokens", None),
                }
        except Exception:
            pass
        return {"content": result, "usage": usage}

    def test_connection(self) -> bool:
        from app.core.runtime_config import RuntimeConfig

        try:
            model = RuntimeConfig(self.settings).load().get("openai_model", "gpt-4.1-mini")
            self.chat_completion(
                system_prompt="You are a test assistant.",
                user_prompt="Say OK.",
                model=model,
                temperature=0.0,
                max_tokens=5,
            )
            return True
        except Exception as exc:
            logger.warning("OpenAI connection test failed: %s", exc)
            return False
