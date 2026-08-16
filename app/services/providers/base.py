from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Return a dict with at least 'content' (str) and optionally 'usage' dict."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        ...
