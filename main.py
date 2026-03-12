import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from shared.database import Base, get_engine
from shared.exceptions import AppException

from services.auth.router import router as auth_router
from services.user.router import router as user_router
from services.telnyx_integration.router import router as telnyx_router
from services.ai_config.router import router as ai_config_router
from services.scheduler.router import router as scheduler_router
from services.call_management.router import router as call_management_router
from services.webhook.router import router as webhook_router
from services.notification.router import router as notification_router
from services.billing.router import router as billing_router
from services.admin.router import router as admin_router

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

app = FastAPI(
    title="AI Call Automator",
    description="Microservices-based AI assistant call automation platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


# Include all service routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(telnyx_router)
app.include_router(ai_config_router)
app.include_router(scheduler_router)
app.include_router(call_management_router)
app.include_router(webhook_router)
app.include_router(notification_router)
app.include_router(billing_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup_event() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root() -> dict:
    return {
        "name": "AI Call Automator",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy"}


# Serve frontend static assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/app")
@app.get("/app/{full_path:path}")
async def serve_frontend(full_path: str = "") -> FileResponse:
    """Serve the frontend SPA for all /app routes."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
