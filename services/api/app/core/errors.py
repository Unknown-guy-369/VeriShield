from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"code": error.code, "message": error.message},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        messages = [str(item.get("msg", "Invalid request.")) for item in error.errors()]
        return JSONResponse(
            status_code=400,
            content={"code": "VALIDATION_ERROR", "message": messages},
        )

    @app.exception_handler(413)
    async def handle_payload_too_large(_request: Request, _error: Any) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "code": "UPLOAD_TOO_LARGE",
                "message": "The uploaded file exceeds the configured size limit.",
            },
        )
