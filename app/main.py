from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import auth, tasks, workspaces
from app.core.config import settings
from app.core.logging_config import logger
from app.db.session import Base, engine
from app.domain.task import AuthorizationError, StateConflictError
from app.api import admin, auth, tasks, workspaces

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Tenant Task & Workspace Manager",
    version="1.0.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"validation_error | path={request.url.path} | detail={exc}")
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
def authorization_error_handler(request: Request, exc: AuthorizationError):
    logger.warning(f"authorization_denied | path={request.url.path} | detail={exc}")
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(StateConflictError)
def state_conflict_handler(request: Request, exc: StateConflictError):
    logger.warning(f"state_conflict | path={request.url.path} | detail={exc}")
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"unhandled_server_error | path={request.url.path}", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)
app.include_router(admin.router)