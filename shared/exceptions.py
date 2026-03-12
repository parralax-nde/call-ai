class AppException(Exception):
    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(detail)


class NotFoundException(AppException):
    def __init__(
        self,
        detail: str = "Resource not found",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=404, detail=detail, headers=headers)


class UnauthorizedException(AppException):
    def __init__(
        self,
        detail: str = "Not authenticated",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=401, detail=detail, headers=headers)


class ForbiddenException(AppException):
    def __init__(
        self,
        detail: str = "Forbidden",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=403, detail=detail, headers=headers)


class BadRequestException(AppException):
    def __init__(
        self,
        detail: str = "Bad request",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=400, detail=detail, headers=headers)


class ConflictException(AppException):
    def __init__(
        self,
        detail: str = "Conflict",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=409, detail=detail, headers=headers)
