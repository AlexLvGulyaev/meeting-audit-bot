from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import Settings, BASE_DIR
from app.core.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class RuntimeConfig:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._path = self.settings.storage_dir / "config.json"
        self._config: dict[str, Any] | None = None

    def _ensure_storage(self) -> None:
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.settings.storage_dir / "prompts").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge override into base."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = RuntimeConfig._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    @staticmethod
    def _migrate_config(config: dict[str, Any]) -> dict[str, Any]:
        """Remove stale top-level keys that are no longer part of DEFAULT_CONFIG."""
        allowed = set(DEFAULT_CONFIG.keys())
        for key in list(config.keys()):
            if key not in allowed:
                logger.info("Removing stale runtime config key %r", key)
                del config[key]
        return config

    def load(self) -> dict[str, Any]:
        self._ensure_storage()
        if self._config is not None:
            return self._config

        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                loaded = json.loads(raw) if raw.strip() else {}
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read config.json: %s. Using defaults.", exc)
                loaded = {}
        else:
            loaded = {}

        merged = self._migrate_config(self._deep_merge(DEFAULT_CONFIG, loaded))
        self._config = merged
        self.save(merged)
        return merged

    def save(self, config: dict[str, Any]) -> None:
        self._ensure_storage()
        self._path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._config = config

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        config = self.load()
        config[key] = value
        self.save(config)
