from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import Settings
from app.core.default_config import DEFAULT_CONFIG
from app.core.runtime_config import RuntimeConfig
from app.services.audit_log import AuditLogService
from app.services.execution import ExecutionService
from app.services.prompt_loader import PromptLoader
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _log_admin_action(
    request: Request,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    actor = request.cookies.get(COOKIE_NAME, "anonymous")
    AuditLogService().log(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )

COOKIE_NAME = "meeting_audit_admin"
DEMO_TOKEN = "demo-admin-session"
DEMO_SESSION_TTL_SECONDS = 3600


def admin_user_id() -> int:
    return Settings.from_env().admin_user_id


def require_admin(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if token != DEMO_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="/admin/login",
        )
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    settings = Settings.from_env()
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "admin_user_id": settings.admin_user_id,
            "demo_token": DEMO_TOKEN,
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    response: Response,
    token: str = Form(...),
) -> Response:
    if token != DEMO_TOKEN:
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Неверный токен",
                "demo_token": DEMO_TOKEN,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=DEMO_SESSION_TTL_SECONDS)
    resp.set_cookie(
        COOKIE_NAME,
        DEMO_TOKEN,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    return resp


@router.post("/login/demo")
async def login_demo(request: Request) -> Response:
    resp = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=DEMO_SESSION_TTL_SECONDS)
    resp.set_cookie(
        COOKIE_NAME,
        DEMO_TOKEN,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    return resp


@router.post("/logout")
async def logout() -> Response:
    resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _=Depends(require_admin)) -> Response:
    storage = StorageService()
    executions_count = storage.count_execution_sessions()
    audits_count = storage.count_audits()
    recent_audits = storage.list_audits(limit=10)
    runtime_cfg = RuntimeConfig().load()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "executions_count": executions_count,
            "audits_count": audits_count,
            "recent_audits": recent_audits,
            "config": runtime_cfg,
        },
    )


@router.get("/executions", response_class=HTMLResponse)
async def executions_page(
    request: Request,
    page: int = 1,
    status_filter: str | None = None,
    _=Depends(require_admin),
) -> Response:
    per_page = 20
    offset = max(0, page - 1) * per_page
    service = ExecutionService()
    sessions = service.list_sessions(limit=per_page, offset=offset, status=status_filter)
    total = StorageService().count_execution_sessions(status=status_filter)
    page_count = max(1, (total + per_page - 1) // per_page)
    return templates.TemplateResponse(
        "admin/executions.html",
        {
            "request": request,
            "sessions": sessions,
            "page": page,
            "page_count": page_count,
            "total": total,
            "status_filter": status_filter,
        },
    )


@router.get("/executions/{session_id}", response_class=HTMLResponse)
async def execution_detail(
    request: Request,
    session_id: str,
    _=Depends(require_admin),
) -> Response:
    service = ExecutionService()
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return templates.TemplateResponse(
        "admin/execution_detail.html",
        {"request": request, "session": session},
    )


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(
    request: Request,
    page: int = 1,
    _=Depends(require_admin),
) -> Response:
    per_page = 20
    offset = max(0, page - 1) * per_page
    storage = StorageService()
    records = storage.list_audits(limit=per_page, offset=offset)
    total = storage.count_audits()
    page_count = max(1, (total + per_page - 1) // per_page)
    return templates.TemplateResponse(
        "admin/audit.html",
        {
            "request": request,
            "records": records,
            "page": page,
            "page_count": page_count,
            "total": total,
        },
    )


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, _=Depends(require_admin)) -> Response:
    cfg = RuntimeConfig().load()
    prompts = PromptLoader().list_prompts()
    return templates.TemplateResponse(
        "admin/config.html",
        {
            "request": request,
            "config": cfg,
            "default_config": DEFAULT_CONFIG,
            "prompts": prompts,
        },
    )


@router.post("/config")
async def config_update(
    request: Request,
    active_provider: str = Form(...),
    active_model: str = Form(...),
    fallback_provider: str = Form(...),
    fallback_model: str = Form(...),
    prompt_id: str = Form(...),
    _=Depends(require_admin),
) -> Response:
    cfg = RuntimeConfig().load()
    cfg["active_provider"] = active_provider
    cfg["fallback_provider"] = fallback_provider
    cfg["prompt_id"] = prompt_id

    # Persist model per provider so the LLM resolver can read provider-specific keys.
    cfg["active_model"] = active_model
    cfg["fallback_model"] = fallback_model
    if active_provider == "openai":
        cfg["openai_model"] = active_model
    elif active_provider == "gigachat":
        cfg["gigachat_model"] = active_model
    if fallback_provider == "openai":
        cfg["openai_model"] = fallback_model
    elif fallback_provider == "gigachat":
        cfg["gigachat_model"] = fallback_model

    RuntimeConfig().save(cfg)
    _log_admin_action(
        request, "update", "config",
        details={"providers": [active_provider, fallback_provider], "prompt_id": prompt_id},
    )
    return RedirectResponse(url="/admin/config", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request, _=Depends(require_admin)) -> Response:
    loader = PromptLoader()
    prompts = loader.list_prompts()
    return templates.TemplateResponse(
        "admin/prompts.html",
        {"request": request, "prompts": prompts},
    )


@router.get("/prompts/{prompt_id}/edit", response_class=HTMLResponse)
async def prompt_edit_page(
    request: Request,
    prompt_id: str,
    _=Depends(require_admin),
) -> Response:
    loader = PromptLoader()
    prompt = loader.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return templates.TemplateResponse(
        "admin/prompt_edit.html",
        {"request": request, "prompt_id": prompt_id, "prompt": prompt},
    )


@router.post("/prompts/{prompt_id}/edit")
async def prompt_edit_submit(
    request: Request,
    prompt_id: str,
    content: str = Form(...),
    _=Depends(require_admin),
) -> Response:
    loader = PromptLoader()
    if not loader.base_exists(prompt_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    loader.save_custom_prompt(prompt_id, content)
    _log_admin_action(
        request, "update", "prompt", resource_id=prompt_id,
        details={"custom": True, "chars": len(content)},
    )
    return RedirectResponse(url="/admin/prompts", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/config", response_class=JSONResponse)
async def api_config(_=Depends(require_admin)) -> dict[str, Any]:
    return RuntimeConfig().load()


@router.get("/api/executions", response_class=JSONResponse)
async def api_executions(
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    _=Depends(require_admin),
) -> dict[str, Any]:
    service = ExecutionService()
    sessions = service.list_sessions(limit=limit, offset=offset, status=status_filter)
    return {"items": sessions, "total": StorageService().count_execution_sessions(status=status_filter)}


@router.get("/api/audit", response_class=JSONResponse)
async def api_audit(
    limit: int = 50,
    offset: int = 0,
    _=Depends(require_admin),
) -> dict[str, Any]:
    storage = StorageService()
    return {"items": storage.list_audits(limit=limit, offset=offset), "total": storage.count_audits()}
