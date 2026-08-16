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
                        prompt_id TEXT NULL,
                        mime_type TEXT NULL,
                        file_size BIGINT NULL,
                        duration INT NULL,
                        storage_filename TEXT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE video_audits
                    ADD COLUMN IF NOT EXISTS storage_filename TEXT NULL;
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
                        storage_filename TEXT NULL,
                        status TEXT NOT NULL,
                        video_audit_id BIGINT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE execution_sessions
                    ADD COLUMN IF NOT EXISTS storage_filename TEXT NULL;
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
                        user_id TEXT NULL,
                        user_name TEXT NULL,
                        user_role TEXT NULL,
                        ip_address TEXT NULL,
                        action TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NULL,
                        details JSONB NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE admin_audit_log
                    ADD COLUMN IF NOT EXISTS user_id TEXT NULL,
                    ADD COLUMN IF NOT EXISTS user_name TEXT NULL,
                    ADD COLUMN IF NOT EXISTS user_role TEXT NULL,
                    ADD COLUMN IF NOT EXISTS ip_address TEXT NULL;
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
        mime_type: str | None = None,
        file_size: int | None = None,
        duration: int | None = None,
        storage_filename: str | None = None,
    ) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO video_audits (
                        chat_id, user_id, username, file_id, file_unique_id,
                        filename, transcript, analysis, status, error_message,
                        provider, prompt_id, mime_type, file_size, duration, storage_filename
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        chat_id, user_id, username, file_id, file_unique_id,
                        filename, transcript, analysis, status, error_message,
                        provider, prompt_id, mime_type, file_size, duration, storage_filename,
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
        storage_filename: str | None = None,
        status: str,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_sessions (session_id, chat_id, user_id, username, file_id, filename, storage_filename, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (session_id, chat_id, user_id, username, file_id, filename, storage_filename, status),
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
        period: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if period == "24h":
            conditions.append("created_at >= NOW() - INTERVAL '24 hours'")
        elif period == "7d":
            conditions.append("created_at >= NOW() - INTERVAL '7 days'")
        elif period == "30d":
            conditions.append("created_at >= NOW() - INTERVAL '30 days'")
        if q:
            conditions.append("filename ILIKE %s")
            params.append(f"%{q}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"""
            SELECT session_id, chat_id, user_id, username, file_id, filename, storage_filename,
                   status, created_at, updated_at, video_audit_id
            FROM execution_sessions
            {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_execution_sessions(
        self,
        status: str | None = None,
        period: str | None = None,
        q: str | None = None,
    ) -> int:
        conditions = []
        params: list[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if period == "24h":
            conditions.append("created_at >= NOW() - INTERVAL '24 hours'")
        elif period == "7d":
            conditions.append("created_at >= NOW() - INTERVAL '7 days'")
        elif period == "30d":
            conditions.append("created_at >= NOW() - INTERVAL '30 days'")
        if q:
            conditions.append("filename ILIKE %s")
            params.append(f"%{q}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT COUNT(*) FROM execution_sessions {where};"
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                return row[0] if row else 0

    def get_execution_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_id, chat_id, user_id, username, file_id, filename, storage_filename,
                           status, created_at, updated_at, video_audit_id
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

    def update_execution_session_video_audit_id(
        self, session_id: str, video_audit_id: int
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE execution_sessions
                    SET video_audit_id = %s, updated_at = NOW()
                    WHERE session_id = %s;
                    """,
                    (video_audit_id, session_id),
                )
            conn.commit()

    def update_execution_session_storage_filename(
        self, session_id: str, storage_filename: str
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE execution_sessions
                    SET storage_filename = %s, updated_at = NOW()
                    WHERE session_id = %s;
                    """,
                    (storage_filename, session_id),
                )
            conn.commit()

    def get_video_audit(self, video_audit_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, created_at, chat_id, user_id, username, file_id,
                           file_unique_id, filename, transcript, analysis, status,
                           error_message, provider, prompt_id, mime_type, file_size, duration, storage_filename
                    FROM video_audits
                    WHERE id = %s;
                    """,
                    (video_audit_id,),
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
        user_id: str | None = None,
        user_name: str | None = None,
        user_role: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        import json

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO admin_audit_log (
                        actor, user_id, user_name, user_role, ip_address,
                        action, resource_type, resource_id, details
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        actor, user_id, user_name, user_role, ip_address,
                        action, resource_type, resource_id, json.dumps(details or {}),
                    ),
                )
            conn.commit()

    def list_admin_audit(
        self,
        limit: int = 100,
        offset: int = 0,
        period: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if period == "24h":
            conditions.append("created_at >= NOW() - INTERVAL '24 hours'")
        elif period == "7d":
            conditions.append("created_at >= NOW() - INTERVAL '7 days'")
        elif period == "30d":
            conditions.append("created_at >= NOW() - INTERVAL '30 days'")
        if action:
            conditions.append("action = %s")
            params.append(action)
        if resource_type:
            conditions.append("resource_type = %s")
            params.append(resource_type)
        if user_id:
            conditions.append("(actor ILIKE %s OR user_id ILIKE %s OR user_name ILIKE %s OR resource_id ILIKE %s)")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"""
            SELECT id, created_at, actor, user_id, user_name, user_role, ip_address,
                   action, resource_type, resource_id, details
            FROM admin_audit_log
            {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def count_admin_audit(
        self,
        period: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: str | None = None,
    ) -> int:
        conditions = []
        params: list[Any] = []
        if period == "24h":
            conditions.append("created_at >= NOW() - INTERVAL '24 hours'")
        elif period == "7d":
            conditions.append("created_at >= NOW() - INTERVAL '7 days'")
        elif period == "30d":
            conditions.append("created_at >= NOW() - INTERVAL '30 days'")
        if action:
            conditions.append("action = %s")
            params.append(action)
        if resource_type:
            conditions.append("resource_type = %s")
            params.append(resource_type)
        if user_id:
            conditions.append("(actor ILIKE %s OR user_id ILIKE %s OR user_name ILIKE %s OR resource_id ILIKE %s)")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
            params.append(f"%{user_id}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT COUNT(*) FROM admin_audit_log {where};"
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
                return row[0] if row else 0

    def list_admin_audit_actions(self) -> list[str]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT DISTINCT action FROM admin_audit_log ORDER BY action;"
                )
                return [row[0] for row in cursor.fetchall() if row[0]]

    def list_admin_audit_resource_types(self) -> list[str]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT DISTINCT resource_type FROM admin_audit_log ORDER BY resource_type;"
                )
                return [row[0] for row in cursor.fetchall() if row[0]]

    def health_check(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    return cursor.fetchone() is not None
        except Exception:
            return False
