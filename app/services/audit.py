from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.core.runtime_config import RuntimeConfig
from app.services.providers.factory import get_provider
from app.services.prompt_loader import PromptLoader
from app.utils.text import strip_markdown_fence

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Ты проводишь аудит диалога по строгим правилам из архитектурного документа. "
    "Следуй правилам точно и не добавляй лишних пояснений."
)


class AuditService:
    def __init__(
        self,
        settings: Settings | None = None,
        runtime_config: RuntimeConfig | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.runtime_config = runtime_config or RuntimeConfig(self.settings)
        self.prompt_loader = prompt_loader or PromptLoader(self.settings)

    def analyze(self, transcript: str) -> dict[str, Any]:
        config = self.runtime_config.load()
        prompt_id = config.get("prompt_id", "onboarding")
        provider_id = config.get("active_provider", "openai")
        fallback_id = config.get("fallback_provider")
        provider_cfg = config.get("providers", {}).get(provider_id, {})
        temperature = float(provider_cfg.get("temperature", 0.1))
        max_tokens = int(provider_cfg.get("max_tokens", 2048))

        audit_prompt = self.prompt_loader.load_prompt(prompt_id)
        model = self._resolve_model(provider_id, config)

        user_prompt = (
            f"{audit_prompt}\n\n"
            "Ниже транскрипт для аудита.\n"
            "<transcript>\n"
            f"{transcript}\n"
            "</transcript>"
        )

        try:
            provider = get_provider(provider_id, self.settings)
            provider_response = provider.chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            analysis = strip_markdown_fence(provider_response["content"])
            usage = provider_response.get("usage")
            return {
                "analysis": analysis,
                "provider": provider_id,
                "prompt_id": prompt_id,
                "model": model,
                "tokens_in": usage.get("prompt_tokens") if usage else None,
                "tokens_out": usage.get("completion_tokens") if usage else None,
                "tokens_total": usage.get("total_tokens") if usage else None,
            }
        except Exception as exc:
            logger.warning("Primary provider %s failed: %s", provider_id, exc)
            if fallback_id and fallback_id != provider_id:
                try:
                    fallback_model = self._resolve_model(fallback_id, config)
                    provider = get_provider(fallback_id, self.settings)
                    fallback_cfg = config.get("providers", {}).get(fallback_id, {})
                    provider_response = provider.chat_completion(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        model=fallback_model,
                        temperature=float(fallback_cfg.get("temperature", 0.1)),
                        max_tokens=int(fallback_cfg.get("max_tokens", 2048)),
                    )
                    analysis = strip_markdown_fence(provider_response["content"])
                    usage = provider_response.get("usage")
                    return {
                        "analysis": analysis,
                        "provider": fallback_id,
                        "prompt_id": prompt_id,
                        "model": fallback_model,
                        "tokens_in": usage.get("prompt_tokens") if usage else None,
                        "tokens_out": usage.get("completion_tokens") if usage else None,
                        "tokens_total": usage.get("total_tokens") if usage else None,
                    }
                except Exception as fb_exc:
                    logger.warning("Fallback provider %s failed: %s", fallback_id, fb_exc)
            return {
                "analysis": self._fallback_analysis(audit_prompt),
                "provider": "fallback_static",
                "prompt_id": prompt_id,
                "model": None,
                "tokens_in": None,
                "tokens_out": None,
                "tokens_total": None,
            }

    def _resolve_model(self, provider_id: str, config: dict[str, Any]) -> str:
        if provider_id == "openai":
            return str(config.get("openai_model", "gpt-4.1-mini"))
        if provider_id == "gigachat":
            return str(config.get("gigachat_model", "GigaChat"))
        return str(config.get("model", "unknown"))

    def _fallback_analysis(self, audit_prompt: str) -> str:
        return (
            "Аудит не выполнен: LLM-провайдеры недоступны.\n\n"
            "Рекомендую проверить:\n"
            "* API-ключи и баланс провайдера.\n"
            "* Настройки провайдера в /admin.\n\n"
            "Транскрипт сохранён; повторите попытку позже."
        )
