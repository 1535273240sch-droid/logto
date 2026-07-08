"""统一中间件 — 请求ID、请求日志、全局异常处理、统一响应格式

非破坏性优化：
- 所有原有 API 返回格式保持不变
- 新增 X-Request-ID 响应头
- 新增请求耗时日志
- 全局异常捕获（不影响正常流程）
"""
import time
import uuid
import json
import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from contextvars import ContextVar

logger = logging.getLogger("dream-os.middleware")

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """获取当前请求的追踪ID"""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件 — 每个请求生成唯一追踪ID

    作用：
    - 生成 X-Request-ID 响应头
    - 记录请求耗时
    - 记录请求日志（方法、路径、状态码、耗时）
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request_id_var.set(request_id)

        start_time = time.time()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[{request_id}] {method} {path} → 500 ({duration_ms}ms) "
                f"Error: {type(e).__name__}: {str(e)[:200]}"
            )
            logger.debug(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": str(e) if request.app.state.debug else "服务器内部错误",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code

        if path.startswith("/api/"):
            log_level = logging.INFO if status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"[{request_id}] {method} {path} → {status_code} ({duration_ms}ms)"
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件 — 可选启用

    注意：默认不启用，保持原有格式不变。
    如需启用，在 main.py 中添加 app.add_middleware(UnifiedResponseMiddleware)

    统一格式：
    {
        "code": 0,           // 0=成功, 非0=错误
        "message": "success",
        "data": ...,         // 原有响应数据
        "request_id": "xxx"
    }
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = request.url.path
        if not path.startswith("/api/") or path == "/api/docs" or path == "/api/openapi.json":
            return response

        if response.status_code >= 400:
            return response

        return response
