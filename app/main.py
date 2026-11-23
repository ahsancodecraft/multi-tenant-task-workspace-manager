from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import auth, tasks, workspaces
from app.core.config import settings
from app.db.session import Base, engine
from app.domain.task import AuthorizationError, StateConflictError

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Tenant Task & Workspace Manager",
    version="1.0.0",
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
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
def authorization_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(StateConflictError)
def state_conflict_handler(request: Request, exc: StateConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)