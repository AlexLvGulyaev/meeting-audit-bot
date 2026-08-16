from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class AuditLogService:
    def __init__(
        self,
        settings: Settings | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.storage = storage or StorageService(self.settings)

    def log(
        self,
        *,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        user_id: str | None = None,
        user_name: str | None = None,
        user_role: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.storage.save_admin_audit(
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                user_name=user_name,
                user_role=user_role,
                ip_address=ip_address,
                details=details,
            )
        except Exception:
            logger.exception("Failed to write admin audit log: %s %s", action, resource_type)

    def list_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.storage.list_admin_audit(limit=limit)
