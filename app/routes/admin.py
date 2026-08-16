from __future__ import annotations

import datetime as dt
import json
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import Settings
from app.core.default_config import DEFAULT_CONFIG
from app.core.runtime_config import RuntimeConfig
from app.services.audit_log import AuditLogService
from app.services.execution import ExecutionService
from app.services.prompt_loader import PromptLoader
from app.services.providers.factory import get_provider
from app.services.storage import StorageService
from app.utils.text import strip_markdown_fence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _fmt_dt(value: Any, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if value is None:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime(fmt)
    if isinstance(value, str):
        return value[: len(fmt)] if len(value) >= len(fmt) else value
    return str(value)


templates.env.filters["dtformat"] = _fmt_dt


def _json_dumps(value: Any) -> str:
    import uuid

    def default(o: Any) -> Any:
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, dt.datetime):
            return o.isoformat()
        raise TypeError

    return json.dumps(value, ensure_ascii=False, indent=2, default=default)


templates.env.globals["_json_dumps"] = _json_dumps
templates.env.filters["strip_markdown_fence"] = strip_markdown_fence

COOKIE_NAME = "meeting_audit_admin"
DEMO_SESSION_TTL_SECONDS = 3600
PAGE_LIMIT = 7


def _admin_tokens() -> tuple[str, str]:
    settings = Settings.from_env()
    return settings.admin_token, settings.admin_demo_token


def admin_user_id() -> int:
    return Settings.from_env().admin_user_id


@dataclass
class AdminIdentity:
    token: str
    is_demo: bool
    display_name: str


def admin_auth(request: Request) -> AdminIdentity:
    token = request.cookies.get(COOKIE_NAME)
    admin_token, admin_demo_token = _admin_tokens()
    if token == admin_token:
        return AdminIdentity(token=token, is_demo=False, display_name="admin")
    if token == admin_demo_token:
        return AdminIdentity(token=token, is_demo=True, display_name="demo-admin")
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        detail="/admin/login",
    )


def require_admin_full(identity: AdminIdentity = Depends(admin_auth)) -> AdminIdentity:
    if identity.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Демо-сессия только для чтения",
        )
    return identity


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None
    if request.client:
        return request.client.host
    return None


def _log_admin_action(
    request: Request,
    identity: AdminIdentity,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    AuditLogService().log(
        actor=identity.display_name,
        user_id=identity.display_name,
        user_name=identity.display_name,
        user_role="demo" if identity.is_demo else "admin",
        ip_address=_client_ip(request),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )


def _set_admin_cookie(resp: RedirectResponse, token: str) -> RedirectResponse:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=DEMO_SESSION_TTL_SECONDS)
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    return resp


def _demo_available() -> bool:
    return bool(Settings.from_env().admin_demo_token)


def _normalize_uuid(obj: Any) -> Any:
    """Recursively convert UUIDs to strings for JSON serialization in templates."""
    import uuid

    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _normalize_uuid(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_uuid(v) for v in obj]
    if isinstance(obj, dt.datetime):
        return obj
    return obj


def _enrich_session_processing_time(s: dict[str, Any]) -> None:
    """Вычислить длительность обработки по последнему завершённому шагу пайплайна.

    Не опираемся на session.updated_at, потому что оно может быть сдвинуто
    ручными правками в БД или не связанными обновлениями статуса.
    """
    created_at = s.get("created_at")
    if not created_at:
        s["processing_duration_seconds"] = None
        return
    # Берём время завершения последнего шага, а не session.updated_at,
    # потому что updated_at может быть сдвинут обслуживающими правками.
    end_at = None
    for step in s.get("steps") or []:
        step_end = step.get("updated_at")
        if step_end and (end_at is None or step_end > end_at):
            end_at = step_end
    if end_at and end_at >= created_at:
        s["processing_duration_seconds"] = round((end_at - created_at).total_seconds(), 2)
    else:
        s["processing_duration_seconds"] = None


def _enrich_session_display_meta(s: dict[str, Any]) -> None:
    """Подготовить удобные для шаблона поля: размер, длительность, пользователь."""
    audit = s.get("video_audit") or {}
    if audit is None:
        audit = {}
    s["display_user"] = f"@{audit.get('username') or s.get('username')}" if (audit.get('username') or s.get('username')) else (s.get("user_id") or "—")
    file_size = audit.get("file_size")
    if file_size is None:
        # fallback на метаданные шага download
        for step in s.get("steps") or []:
            if step.get("name") == "download" and step.get("metadata"):
                file_size = step["metadata"].get("size_bytes")
                if file_size is not None:
                    break
    s["display_file_size"] = f"{round(file_size / 1024, 1)} KB" if file_size is not None else "—"
    duration = audit.get("duration")
    s["display_duration"] = f"{duration} с" if duration is not None else "—"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "demo_disabled": not _demo_available(),
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    token: str = Form(...),
) -> Response:
    admin_token, admin_demo_token = _admin_tokens()
    if token not in (admin_token, admin_demo_token):
        _log_admin_action(
            request,
            AdminIdentity(token=token, is_demo=False, display_name="unknown"),
            "admin.login_failed", "admin_session",
            details={"reason": "invalid_token"},
        )
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Неверный токен",
                "demo_disabled": not _demo_available(),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    is_demo = token == admin_demo_token
    identity = AdminIdentity(token=token, is_demo=is_demo, display_name="demo-admin" if is_demo else "admin")
    _log_admin_action(
        request, identity, "admin.login_success", "admin_session",
        details={"entry": "token_form", "is_demo": is_demo},
    )
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return _set_admin_cookie(resp, token)


@router.post("/login/demo")
async def login_demo(request: Request) -> Response:
    _, admin_demo_token = _admin_tokens()
    if not admin_demo_token:
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "demo_unavailable",
                "demo_disabled": True,
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
    identity = AdminIdentity(token=admin_demo_token, is_demo=True, display_name="demo-admin")
    _log_admin_action(
        request, identity, "admin.login_success", "admin_session",
        details={"entry": "demo_button"},
    )
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return _set_admin_cookie(resp, admin_demo_token)


@router.post("/logout")
async def logout(request: Request, identity: AdminIdentity = Depends(admin_auth)) -> Response:
    _log_admin_action(
        request, identity, "admin.logout", "admin_session",
        details={"is_demo": identity.is_demo},
    )
    resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(COOKIE_NAME)
    return resp


def _telegram_status(request: Request) -> tuple[bool, str | None]:
    try:
        telegram_app = getattr(request.app.state, "telegram_app", None)
        if telegram_app is None:
            return False, None
        running = getattr(telegram_app, "running", False)
        return bool(running), getattr(telegram_app.bot, "username", None) if getattr(telegram_app, "bot", None) else None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to read Telegram app state: %s", exc)
        return False, None


def _provider_status(provider_id: str) -> tuple[bool, str | None]:
    try:
        provider = get_provider(provider_id)
        ok = provider.test_connection()
        return ok, None
    except Exception as exc:
        return False, str(exc)


def _provider_configured(provider_id: str) -> bool:
    settings = Settings.from_env()
    if provider_id == "openai":
        return bool(settings.openai_api_key)
    if provider_id == "gigachat":
        return bool(settings.gigachat_auth_key)
    return False


def _prompt_info(prompt_id: str) -> dict[str, Any] | None:
    loader = PromptLoader()
    path = loader._custom_dir() / f"{prompt_id}.md"
    if not path.exists():
        path = loader._base_dir() / f"{prompt_id}.md"
    if not path.exists():
        return None
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime": dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).isoformat(),
    }


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, identity: AdminIdentity = Depends(admin_auth)) -> Response:
    storage = StorageService()
    runtime_cfg = RuntimeConfig().load()
    loader = PromptLoader()
    prompts = loader.list_prompts()

    active_prompt_id = runtime_cfg.get("prompt_id", "onboarding")
    preview_prompt_id = request.query_params.get("prompt_id") or active_prompt_id
    current_prompt = loader.get_prompt(preview_prompt_id)
    prompt_content = current_prompt["content"] if current_prompt else ""

    tg_ok, tg_username = _telegram_status(request)
    db_ok = storage.health_check()
    active_provider = runtime_cfg.get("active_provider", "openai")
    # На странице конфигурации показываем "настроен" по наличию ключа,
    # чтобы вход не блокировался синхронными LLM-вызовами.
    provider_ok = _provider_configured(active_provider)
    openai_ok = _provider_configured("openai")
    gigachat_ok = _provider_configured("gigachat")

    total_audits = storage.count_audits()
    success_executions = storage.count_execution_sessions(status="success")
    failed_executions = storage.count_execution_sessions(status="failed")
    audit_entries = storage.count_audits()

    # Flash-сообщение результата «Проверить» (?test=ok|err&prov=...&msg=...).
    test_result = None
    test_param = request.query_params.get("test")
    if test_param in ("ok", "err"):
        test_result = {
            "ok": test_param == "ok",
            "provider": request.query_params.get("prov", ""),
            "message": request.query_params.get("msg", ""),
        }

    return templates.TemplateResponse(
        "admin/admin.html",
        {
            "request": request,
            "is_demo": identity.is_demo,
            "identity": identity,
            "config": runtime_cfg,
            "default_config": DEFAULT_CONFIG,
            "prompts": prompts,
            "active_prompt_id": preview_prompt_id,
            "saved_active_prompt_id": active_prompt_id,
            "prompt_content": prompt_content,
            "prompt_info": _prompt_info(active_prompt_id),
            "status_postgres": db_ok,
            "status_telegram": tg_ok,
            "status_telegram_username": tg_username,
            "status_provider": provider_ok,
            "status_provider_error": None,
            "status_openai": openai_ok,
            "status_gigachat": gigachat_ok,
            "status_api": True,
            "total_audits": total_audits,
            "success_executions": success_executions,
            "failed_executions": failed_executions,
            "audit_entries": audit_entries,
            "status_json": json.dumps(runtime_cfg, ensure_ascii=False, indent=2),
            "saved": request.query_params.get("saved") == "1",
            "test_result": test_result,
        },
    )


@router.post("/save")
async def admin_save(
    request: Request,
    identity: AdminIdentity = Depends(require_admin_full),
    active_provider: str = Form(...),
    fallback_provider: str = Form(...),
    openai_base_url: str = Form(""),
    openai_model: str = Form(...),
    openai_temperature: float = Form(0.1),
    openai_max_tokens: int = Form(2048),
    gigachat_model: str = Form(...),
    gigachat_temperature: float = Form(0.1),
    gigachat_max_tokens: int = Form(2048),
    prompt_id: str = Form(...),
    prompt_content: str = Form(""),
) -> Response:
    cfg = RuntimeConfig().load()
    cfg["active_provider"] = active_provider
    cfg["fallback_provider"] = fallback_provider
    cfg["openai_model"] = openai_model
    cfg["gigachat_model"] = gigachat_model
    cfg["prompt_id"] = prompt_id

    cfg["providers"] = cfg.get("providers", DEFAULT_CONFIG["providers"]).copy()
    cfg["providers"]["openai"] = {
        **(cfg["providers"].get("openai") or {}),
        "base_url": openai_base_url or None,
        "temperature": openai_temperature,
        "max_tokens": openai_max_tokens,
    }
    cfg["providers"]["gigachat"] = {
        **(cfg["providers"].get("gigachat") or {}),
        "temperature": gigachat_temperature,
        "max_tokens": gigachat_max_tokens,
    }

    RuntimeConfig().save(cfg)

    loader = PromptLoader()
    base_prompt = loader.get_prompt(prompt_id) if loader.base_exists(prompt_id) else None
    base_content = base_prompt["content"] if base_prompt else ""
    custom_path = loader._custom_dir() / f"{prompt_id}.md"

    def _normalize(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()

    prompt_saved = _normalize(prompt_content) != _normalize(base_content)
    if prompt_saved:
        loader.save_custom_prompt(prompt_id, prompt_content)
    elif custom_path.exists():
        custom_path.unlink()

    _log_admin_action(
        request, identity, "admin.config_update", "config",
        resource_id="config.json",
        details={
            "providers": [active_provider, fallback_provider],
            "prompt_id": prompt_id,
            "prompt_saved": prompt_saved,
        },
    )

    return RedirectResponse(url=f"/admin?prompt_id={prompt_id}&saved=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/executions", response_class=HTMLResponse)
async def executions_page(
    request: Request,
    offset: int = 0,
    status: str | None = None,
    period: str | None = None,
    q: str | None = None,
    selected: str | None = None,
    identity: AdminIdentity = Depends(admin_auth),
) -> Response:
    service = ExecutionService()
    storage = StorageService()

    filters = {
        "status": status,
        "period": period,
        "q": q,
    }
    total = storage.count_execution_sessions(status=status, period=period, q=q)
    sessions = service.list_sessions(
        limit=PAGE_LIMIT, offset=offset, status=status, period=period, q=q
    )
    selected_id = selected
    if sessions and not selected_id:
        selected_id = sessions[0]["session_id"]

    # Глобальная нумерация: #1 = самая старая запись, #N = самая новая.
    # Список отсортирован по created_at DESC, поэтому номер уменьшается сверху вниз.
    for i, s in enumerate(sessions):
        s["row_number"] = max(1, total - offset - i)
        s["steps"] = storage.get_execution_steps(s["session_id"])
        s["video_audit"] = None
        if s.get("video_audit_id"):
            s["video_audit"] = storage.get_video_audit(s["video_audit_id"])
        _enrich_session_processing_time(s)
        _enrich_session_display_meta(s)

    sessions = _normalize_uuid(sessions)

    return templates.TemplateResponse(
        "admin/executions.html",
        {
            "request": request,
            "is_demo": identity.is_demo,
            "identity": identity,
            "sessions": sessions,
            "selected_id": selected_id,
            "offset": offset,
            "limit": PAGE_LIMIT,
            "total": total,
            "filters": filters,
        },
    )


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(
    request: Request,
    offset: int = 0,
    period: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    user_id: str | None = None,
    selected: int | None = None,
    identity: AdminIdentity = Depends(admin_auth),
) -> Response:
    storage = StorageService()
    filters = {
        "period": period,
        "action": action,
        "resource_type": resource_type,
        "user_id": user_id,
    }
    total = storage.count_admin_audit(period=period, action=action, resource_type=resource_type, user_id=user_id)
    entries = storage.list_admin_audit(
        limit=PAGE_LIMIT, offset=offset, period=period, action=action, resource_type=resource_type, user_id=user_id
    )
    actions = storage.list_admin_audit_actions()
    resource_types = storage.list_admin_audit_resource_types()
    selected_id = selected
    if entries and not selected_id:
        selected_id = entries[0]["id"]

    entries = _normalize_uuid(entries)

    return templates.TemplateResponse(
        "admin/audit.html",
        {
            "request": request,
            "is_demo": identity.is_demo,
            "identity": identity,
            "entries": entries,
            "selected_id": selected_id,
            "offset": offset,
            "limit": PAGE_LIMIT,
            "total": total,
            "filters": filters,
            "actions": actions,
            "resource_types": resource_types,
        },
    )


def _flash_url(provider_id: str, ok: bool, message: str) -> str:
    from urllib.parse import urlencode

    status = "ok" if ok else "err"
    return f"/admin?{urlencode({'test': status, 'prov': provider_id, 'msg': message})}"


@router.post("/test-provider")
async def admin_test_provider(
    request: Request,
    identity: AdminIdentity = Depends(require_admin_full),
    provider_id: str = Form(...),
) -> Response:
    provider_id = provider_id.strip().lower()
    if provider_id not in ("openai", "gigachat"):
        return RedirectResponse(
            url=_flash_url(provider_id, False, "неизвестный провайдер"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    ok, error = _provider_status(provider_id)
    message = error or ("готов" if ok else "не готов")

    _log_admin_action(
        request, identity, "admin.provider_test", "provider",
        resource_id=provider_id,
        details={"ok": ok, "error": error},
    )
    return RedirectResponse(
        url=_flash_url(provider_id, ok, message),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/api/providers/{provider_id}/test", response_class=JSONResponse)
async def api_test_provider_json(
    request: Request,
    provider_id: str,
    identity: AdminIdentity = Depends(admin_auth),
) -> dict[str, Any]:
    ok, error = _provider_status(provider_id)
    _log_admin_action(
        request, identity, "admin.provider_test", "provider",
        resource_id=provider_id,
        details={"ok": ok, "error": error},
    )
    return {"provider_id": provider_id, "ok": ok, "error": error}


@router.get("/api/executions/{session_id}", response_class=JSONResponse)
async def api_execution_detail(
    session_id: str,
    identity: AdminIdentity = Depends(admin_auth),
) -> dict[str, Any]:
    service = ExecutionService()
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/api/audit/{record_id}", response_class=JSONResponse)
async def api_audit_detail(
    record_id: int,
    identity: AdminIdentity = Depends(admin_auth),
) -> dict[str, Any]:
    storage = StorageService()
    records = storage.list_admin_audit(limit=1000, offset=0)
    record = next((r for r in records if r["id"] == record_id), None)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


@router.get("/api/config", response_class=JSONResponse)
async def api_config(identity: AdminIdentity = Depends(admin_auth)) -> dict[str, Any]:
    return RuntimeConfig().load()


@router.get("/uploads/{filename}")
async def admin_upload_file(
    filename: str,
    identity: AdminIdentity = Depends(admin_auth),
) -> FileResponse:
    settings = Settings.from_env()
    uploads_dir = settings.storage_uploads_dir
    target = (uploads_dir / filename).resolve()
    try:
        target.relative_to(uploads_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename") from exc
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    mime, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        path=target,
        media_type=mime or "application/octet-stream",
        filename=target.name,
        content_disposition_type="inline",
    )
