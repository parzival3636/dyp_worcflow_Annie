from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.config import settings
from backend.db import get_session, create_db_and_tables
from backend.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    create_db_and_tables()
    yield
    # Shutdown logic if any


app = FastAPI(title="Pilot Backend API", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    code = "HTTP_ERROR"
    if isinstance(detail, dict):
        error_msg = detail.get("error", str(detail))
        code = detail.get("code", "HTTP_ERROR")
    else:
        error_msg = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_msg, "code": code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred", "code": "INTERNAL_SERVER_ERROR"},
    )


@app.get("/health")
@app.get("/api/health")
def get_health() -> dict[str, str]:
    db_status = "ok"
    try:
        with get_session() as session:
            session.exec(text("SELECT 1")).first()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "telegram": "ok",
        "github": "ok",
        "llm": "ok",
        "db": db_status,
    }


# Include REST API routes
app.include_router(router)
