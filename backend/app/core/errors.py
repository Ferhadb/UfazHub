"""One error envelope for every failure: {code, message, fields?, request_id}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: dict[str, str] | None = None
    request_id: str | None = None


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.fields = fields
        self.headers = headers


class NotFound(AppError):
    status_code, code = 404, "not_found"


class Forbidden(AppError):
    status_code, code = 403, "forbidden"


class Unauthorized(AppError):
    status_code, code = 401, "unauthorized"


class Conflict(AppError):
    status_code, code = 409, "conflict"


_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "rate_limited",
}


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _json(request: Request, status: int, body: ErrorBody, headers=None) -> JSONResponse:
    body.request_id = _rid(request)
    return JSONResponse(
        body.model_dump(exclude_none=True), status_code=status, headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _json(
            request,
            exc.status_code,
            ErrorBody(code=exc.code, message=exc.message, fields=exc.fields),
            exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = _STATUS_CODES.get(exc.status_code, "error")
        return _json(
            request,
            exc.status_code,
            ErrorBody(code=code, message=str(exc.detail)),
            getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        fields = {}
        for err in exc.errors():
            # Only the leading source marker goes; a field may itself be called "body".
            parts = (
                err["loc"][1:]
                if err["loc"][0] in ("body", "query", "path")
                else err["loc"]
            )
            loc = [str(p) for p in parts]
            fields[".".join(loc) or "_"] = err["msg"]
        return _json(
            request,
            422,
            ErrorBody(code="validation_error", message="Invalid input", fields=fields),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return _json(
            request, 500, ErrorBody(code="internal_error", message="Something broke")
        )
