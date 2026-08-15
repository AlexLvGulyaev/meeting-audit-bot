from __future__ import annotations

import datetime as dt
import logging
import uuid
from dataclasses import asdict
from typing import Any

from app.core.config import Settings
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self, settings: Settings | None = None, storage: StorageService | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.storage = storage or StorageService(self.settings)

    def start_session(
        self,
        chat_id: int | None,
        user_id: int | None,
        username: str | None,
        file_id: str | None,
        filename: str | None,
    ) -> str:
        session_id = str(uuid.uuid4())
        self.storage.insert_execution_session(
            session_id=session_id,
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            file_id=file_id,
            filename=filename,
            status="running",
        )
        return session_id

    def finish_session(self, session_id: str, status: str) -> None:
        self.storage.update_execution_session_status(session_id, status)

    def start_step(self, session_id: str, name: str, metadata: dict[str, Any] | None = None) -> str:
        step_id = str(uuid.uuid4())
        self.storage.insert_execution_step(
            step_id=step_id,
            session_id=session_id,
            name=name,
            status="running",
            metadata=metadata,
        )
        return step_id

    def finish_step(
        self,
        session_id: str,
        name: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.storage.update_execution_step_status(session_id, name, status, metadata)

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.storage.list_execution_sessions(limit=limit, offset=offset, status=status)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.storage.get_execution_session(session_id)
        if not session:
            return None
        steps = self.storage.get_execution_steps(session_id)
        result = dict(session)
        result["steps"] = [dict(row) for row in steps]
        return result
