"""Dream OS - AI Operating System - 主入口 + 前端静态文件服务"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import get_settings
from .db.session import init_db
from .api.routes import task, agent, memory, settings as settings_routes, stream, media, voice
from .api.routes import tool_center, project
from .api import ws

FRONTEND_DIR = "/dream-os/frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库"""
    settings = get_settings()
    print(f"🚀 {settings.project_name} v{settings.version} starting...")
    await init_db()
    print("✅ Database initialized")
    if os.path.isdir(FRONTEND_DIR):
        files = os.listdir(FRONTEND_DIR)
        print(f"📁 Frontend static files: {len(files)} items")
    yield
    print("👋 Dream OS shutting down...")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 路由
    app.include_router(task.router)
    app.include_router(agent.router)
    app.include_router(memory.router)
    app.include_router(settings_routes.router)
    app.include_router(stream.router)
    app.include_router(media.router)
    app.include_router(voice.router)
    app.include_router(ws.router)
    app.include_router(tool_center.router)
    app.include_router(project.router)

    # 健康检查
    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "project": settings.project_name,
            "version": settings.version,
            "model": settings.openai_model,
        }

    # 可用工具
    @app.get("/api/tools")
    async def list_tools():
        from .core.tool_registry import ToolRegistry
        tr = ToolRegistry()
        return {"tools": tr.list_tools(), "count": len(tr.list_tools())}

    # 静态文件服务 — 前端页面 (必须在所有 API 路由之后)
    # 访问 / 即为 project-workspace.html (通过 index.html)
    if os.path.isdir(FRONTEND_DIR):
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
        print(f"✅ Frontend mounted: {FRONTEND_DIR}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )