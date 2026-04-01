import json
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import engine, Base
from app.database.schema_patch import patch_sqlite_schema
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User

from app.api.auth_routes import router as auth_router
from app.api.goal_routes import router as goal_router
from app.api.task_routes import router as task_router

app = FastAPI(title="AI Execution Engine")

Base.metadata.create_all(bind=engine)
patch_sqlite_schema(engine)

_DEBUG_LOG_PATHS = [
    # Workspace root (required by debug-mode harness)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "debug-6f13b9.log")),
    # Fallback: backend root (in case server CWD causes confusion)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "debug-6f13b9.log")),
]


def _dbg_log(*, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "6f13b9",
            "runId": "repro",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        for path in _DEBUG_LOG_PATHS:
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass
    except Exception:
        pass
    # endregion


@app.on_event("startup")
def _debug_startup_probe() -> None:
    # region agent log
    _dbg_log(
        hypothesis_id="H5",
        location="app/main.py:_debug_startup_probe",
        message="App startup probe",
        data={"log_paths": _DEBUG_LOG_PATHS},
    )
    # endregion


@app.middleware("http")
async def debug_exception_logger(request: Request, call_next):
    # region agent log
    _dbg_log(
        hypothesis_id="H5",
        location="app/main.py:debug_exception_logger",
        message="Request start",
        data={"method": request.method, "path": request.url.path},
    )
    # endregion
    try:
        response = await call_next(request)
        response.headers["X-Debug-Session"] = "6f13b9"
        # region agent log
        _dbg_log(
            hypothesis_id="H5",
            location="app/main.py:debug_exception_logger",
            message="Request end",
            data={
                "method": request.method,
                "path": request.url.path,
                "status_code": getattr(response, "status_code", None),
            },
        )
        # endregion
        return response
    except Exception as exc:
        # region agent log
        _dbg_log(
            hypothesis_id="H5",
            location="app/main.py:debug_exception_logger",
            message="Unhandled exception",
            data={
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        # endregion
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok"}

app.include_router(auth_router)
app.include_router(goal_router, prefix="/goals")
app.include_router(task_router, prefix="/tasks")