from __future__ import annotations

import logging
import re
from pathlib import Path

from app.core.config import BASE_DIR, Settings

logger = logging.getLogger(__name__)

REQUIRED_BLOCKS = {
    "Роль",
    "Задача",
    "Критерии оценки",
    "Процесс аудита",
    "Инструкции по выводу",
    "Ограничения",
    "Формат ответа",
}


class PromptLoader:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    def _base_dir(self) -> Path:
        return self.settings.prompts_dir / "v1"

    def _custom_dir(self) -> Path:
        return self.settings.storage_dir / "prompts"

    @staticmethod
    def _read_title(path: Path) -> str | None:
        """Читает первую строку title: ... из markdown-файла промпта."""
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.lower().startswith("title:"):
                        return stripped[6:].strip()
                    break
        except Exception:
            pass
        return None

    def list_prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        seen: set[str] = set()
        for directory in (self._custom_dir(), self._base_dir()):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.md")):
                prompt_id = path.stem
                if prompt_id in seen:
                    continue
                seen.add(prompt_id)
                is_custom = directory == self._custom_dir()
                title = self._read_title(path)
                display_name = title or prompt_id.replace("-", " ").title()
                prompts.append(
                    {
                        "id": prompt_id,
                        "name": display_name,
                        "title": display_name,
                        "editable": str(is_custom),
                        "source": "custom" if is_custom else "base",
                        "path": str(path.relative_to(BASE_DIR)),
                    }
                )
        return prompts

    def load_prompt(self, prompt_id: str) -> str:
        custom_path = self._custom_dir() / f"{prompt_id}.md"
        base_path = self._base_dir() / f"{prompt_id}.md"
        path = custom_path if custom_path.exists() else base_path
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_id}.md")
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Prompt file is empty: {path}")
        return content

    def validate_prompt(self, content: str) -> tuple[bool, list[str]]:
        found: set[str] = set()
        missing: list[str] = []
        for block in REQUIRED_BLOCKS:
            pattern = rf"^##\s+{re.escape(block)}\s*$"
            if re.search(pattern, content, flags=re.IGNORECASE | re.MULTILINE):
                found.add(block)
            else:
                missing.append(f"## {block}")
        return len(missing) == 0, missing

    def base_exists(self, prompt_id: str) -> bool:
        return (self._base_dir() / f"{prompt_id}.md").exists()

    def get_prompt(self, prompt_id: str) -> dict[str, str] | None:
        custom_path = self._custom_dir() / f"{prompt_id}.md"
        base_path = self._base_dir() / f"{prompt_id}.md"
        path = custom_path if custom_path.exists() else base_path
        if not path.exists():
            return None
        return {
            "id": prompt_id,
            "content": path.read_text(encoding="utf-8"),
            "source": "custom" if path == custom_path else "base",
        }

    def save_custom_prompt(self, prompt_id: str, content: str) -> Path:
        self._custom_dir().mkdir(parents=True, exist_ok=True)
        path = self._custom_dir() / f"{prompt_id}.md"
        path.write_text(content, encoding="utf-8")
        return path
