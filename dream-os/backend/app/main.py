"""Dream OS Backend - Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api.routes.stream import router as stream_router
from .api.routes.plugin import router as plugin_router
from .api.routes.settings import router as settings_router
from .api.routes.ai_engine import router as ai_engine_router
from .api.routes.mcp import router as mcp_router
from .db.session import init_db
from .core.mcp_manager import init_mcp, shutdown_mcp

app = FastAPI(title="Dream OS V6 Backend", version="1.0.0")

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream_router)
app.include_router(plugin_router)
app.include_router(settings_router)
app.include_router(ai_engine_router)
app.include_router(mcp_router)


@app.on_event("shutdown")
async def shutdown():
    await shutdown_mcp()


@app.on_event("startup")
async def startup():
    await init_db()
    await init_mcp()


@app.get("/")
async def root():
    return {"service": "Dream OS V6 Backend", "status": "running"}
