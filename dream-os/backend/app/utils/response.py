"""统一响应工具 — 可选使用，不影响现有接口

提供标准化的 API 响应格式。
原有接口保持不变，新接口可以选择使用这些工具函数。
"""
from typing import Any, Optional
from fastapi.responses import JSONResponse
from ..middleware import get_request_id


def success(data: Any = None, message: str = "success", code: int = 0) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
    }


def error(message: str, code: int = 1, data: Any = None,
          http_status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={
            "code": code,
            "message": message,
            "data": data,
            "request_id": get_request_id(),
        },
    )


def ok(data: Any = None, message: str = "success") -> dict:
    return success(data, message)


def bad_request(message: str = "Bad Request", code: int = 400) -> JSONResponse:
    return error(message, code, http_status=400)


def unauthorized(message: str = "Unauthorized", code: int = 401) -> JSONResponse:
    return error(message, code, http_status=401)


def forbidden(message: str = "Forbidden", code: int = 403) -> JSONResponse:
    return error(message, code, http_status=403)


def not_found(message: str = "Not Found", code: int = 404) -> JSONResponse:
    return error(message, code, http_status=404)


def server_error(message: str = "Internal Server Error", code: int = 500) -> JSONResponse:
    return error(message, code, http_status=500)


def paginated(items: list, total: int, page: int = 1,
              page_size: int = 20, message: str = "success") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
        "request_id": get_request_id(),
    }
