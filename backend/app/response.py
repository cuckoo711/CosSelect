from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Business-level error carrying a code and message."""

    def __init__(self, msg: str, code: int = 1, status_code: int = 200):
        self.msg = msg
        self.code = code
        self.status_code = status_code
        super().__init__(msg)


def ok(data: Any = None, msg: str = "success") -> dict:
    return {"code": 0, "data": data, "msg": msg}


def fail(msg: str, code: int = 1, data: Any = None) -> dict:
    return {"code": code, "data": data, "msg": msg}


def register_exception_handlers(app):
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(exc.msg, exc.code),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(str(exc.detail), code=exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        errors = jsonable_encoder(exc.errors())
        # surface the first human-readable message
        msg = "参数校验失败"
        if errors and isinstance(errors, list) and errors[0].get("msg"):
            msg = errors[0]["msg"]
        return JSONResponse(
            status_code=422,
            content=fail(msg, code=422, data=errors),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=fail(f"服务器内部错误: {exc}", code=500),
        )
