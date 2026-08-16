import asyncio
import datetime as dt
from starlette.requests import Request
from fastapi.templating import Jinja2Templates
from app.routes.admin import _normalize_uuid, _json_dumps, _fmt_dt
from app.services.storage import StorageService
from app.services.execution import ExecutionService

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["dtformat"] = _fmt_dt
templates.env.globals["_json_dumps"] = _json_dumps

svc = ExecutionService()
st = StorageService()
sessions = svc.list_sessions(limit=7, offset=0)
for s in sessions:
    s["steps"] = st.get_execution_steps(s["session_id"])
    s["video_audit"] = None
    if s.get("video_audit_id"):
        s["video_audit"] = st.get_video_audit(s["video_audit_id"])

sessions = _normalize_uuid(sessions)

scope = {
    "type": "http",
    "method": "GET",
    "path": "/admin/executions",
    "query_string": b"",
    "headers": [],
}

async def run():
    request = Request(scope)
    ctx = {
        "request": request,
        "is_demo": False,
        "identity": None,
        "sessions": sessions,
        "selected_id": sessions[0]["session_id"],
        "offset": 0,
        "limit": 7,
        "total": len(sessions),
        "filters": {},
    }
    try:
        out = templates.get_template("admin/executions.html").render(ctx)
        print("OK", len(out))
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run())
