from typing import Any

from pydantic import BaseModel


class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


class PaginatedResponse(BaseResponse):
    total: int
    page: int
    per_page: int


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
