from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.exceptions import AppException

from .router import router

app = FastAPI(title="Billing & Payment Service", version="0.1.0")
app.include_router(router)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )
