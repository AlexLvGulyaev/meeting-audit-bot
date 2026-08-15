from __future__ import annotations

import logging
import time
from typing import Any

import psycopg

from app.core.config import Settings

logger = logging.getLogger(__name__)

DB_CONNECTION_RETRIES = 30
DB_CONNECTION_RETRY_DELAY_SECONDS = 2


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    def _connect(self):
        return psycopg.connect(self.settings.database_url)

    def init_tables(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS video_audits (
                        id BIGSERIAL PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        chat_id BIGINT NOT NULL,
                        user_id BIGINT NULL,
                        username TEXT NULL,
                        file_id TEXT NOT NULL,
                        file_unique_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        transcript TEXT NULL,
                        analysis TEXT NULL,
                        status TEXT NOT NULL,
                        error_message TEXT NULL,
                        provider TEXT NULL,
                        prompt_id TEXT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_video_audits_chat_id
                    ON video_audits (chat_id);
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_video_audits_created_at
                    ON video_audits (created_at DESC);
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_sessions (
                        session_id UUID PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        chat_id BIGINT NULL,
                        user_id BIGINT NULL,
                        username TEXT NULL,
                        file_id TEXT NULL,
                        filename TEXT NULL,
                        status TEXT NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_execution_sessions_created_at
                    ON execution_sessions (created_at DESC);
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_steps (
                        step_id UUID PRIMARY KEY,
                        session_id UUID NOT NULL REFERENCES execution_sessions(session_id) ON DELETE CASCADE,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        metadata JSONB NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_execution_steps_session_id
                    ON execution_steps (session_id);
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_audit_log (
                        id BIGSERIAL PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NULL,
                        details JSONB NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created_at
                    ON admin_audit_log (created_at DESC);
                    """
                )
            conn.commit()
        logger.info("Database tables initialized")

    def init_tables_with_retry(self) -> None:
        for attempt in range(1, DB_CONNECTION_RETRIES + 1):
            try:
                self.init_tables()
                return
            except Exception as error:
                logger.warning(
                    "Postgres is not ready yet (attempt %s/%s): %s",
                    attempt,
                    DB_CONNECTION_RETRIES,
                    error,
                )
                time.sleep(DB_CONNECTION_RETRY_DELAY_SECONDS)
        raise RuntimeError("Could not initialize Postgres schema after multiple attempts.")

    def save_audit(
        self,
        *,
        chat_id: int,
        user_id: int | None,
        username: str | None,
        file_id: str,
        file_unique_id: str,
        filename: str,
        transcript: str | None,
        analysis: str | None,
        status: str,
        error_message: str | None,
        provider: str | None = None,
        prompt_id: str | None = None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO video_audits (
                        chat_id, user_id, username, file_id, file_unique_id,
                        filename, transcript, analysis, status, error_message,
                        provider, prompt_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        chat_id, user_id, username, file_id, file_unique_id,
                        filename, transcript, analysis, status, error_message,
                        provider, prompt_id,
                    ),
                )
                row = cursor.fetchone()
            conn.commit()
            return row[0] if row else 0

    def count_uploads_today(self, user_id: int | None) -> int:
        if user_id is None:
            return 0
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM video_audits
                    WHERE user_id = %s
                      AND created_at >= CURRENT_DATE
                      AND status = 'success';
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                return row[0] if row else 0

    def list_audits(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, created_at, chat_id, user_id, username, file_id,
                           file_unique_id, filename, status, provider, prompt_id
                    FROM video_audits
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                    """,
                    (limit, offset),
                )
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_audits(self) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM video_audits;")
                row = cursor.fetchone()
                return row[0] if row else 0

    def insert_execution_session(
        self,
        *,
        session_id: str,
        chat_id: int | None,
        user_id: int | None,
        username: str | None,
        file_id: str | None,
        filename: str | None,
        status: str,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_sessions (session_id, chat_id, user_id, username, file_id, filename, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (session_id, chat_id, user_id, username, file_id, filename, status),
                )
            conn.commit()

    def update_execution_session_status(self, session_id: str, status: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE execution_sessions
                    SET status = %s, updated_at = NOW()
                    WHERE session_id = %s;
                    """,
                    (status, session_id),
                )
            conn.commit()

    def list_execution_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if status:
                    cursor.execute(
                        """
                        SELECT session_id, chat_id, user_id, username, file_id, filename,
                               status, created_at, updated_at
                        FROM execution_sessions
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s;
                        """,
                        (status, limit, offset),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT session_id, chat_id, user_id, username, file_id, filename,
                               status, created_at, updated_at
                        FROM execution_sessions
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s;
                        """,
                        (limit, offset),
                    )
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_execution_sessions(self, status: str | None = None) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                if status:
                    cursor.execute(
                        "SELECT COUNT(*) FROM execution_sessions WHERE status = %s;",
                        (status,),
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM execution_sessions;")
                row = cursor.fetchone()
                return row[0] if row else 0

    def get_execution_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_id, chat_id, user_id, username, file_id, filename,
                           status, created_at, updated_at
                    FROM execution_sessions
                    WHERE session_id = %s;
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

    def insert_execution_step(
        self,
        *,
        step_id: str,
        session_id: str,
        name: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        import json

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_steps (step_id, session_id, name, status, metadata)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (step_id, session_id, name, status, json.dumps(metadata) if metadata is not None else None),
                )
            conn.commit()

    def update_execution_step_status(
        self,
        session_id: str,
        name: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        import json

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE execution_steps
                    SET status = %s, metadata = COALESCE(%s, metadata), updated_at = NOW()
                    WHERE session_id = %s AND name = %s;
                    """,
                    (status, json.dumps(metadata) if metadata is not None else None, session_id, name),
                )
            conn.commit()

    def get_execution_steps(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT step_id, session_id, name, status, metadata, created_at, updated_at
                    FROM execution_steps
                    WHERE session_id = %s
                    ORDER BY created_at ASC;
                    """,
                    (session_id,),
                )
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def save_admin_audit(
        self,
        *,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        import json

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO admin_audit_log (actor, action, resource_type, resource_id, details)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (actor, action, resource_type, resource_id, json.dumps(details or {})),
                )
            conn.commit()

    def list_admin_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, created_at, actor, action, resource_type, resource_id, details
                    FROM admin_audit_log
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def health_check(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    return cursor.fetchone() is not None
        except Exception:
            return False
