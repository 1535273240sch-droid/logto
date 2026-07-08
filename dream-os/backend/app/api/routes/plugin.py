"""Plugin Route - 插件 API 端点"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...core.plugins import match_plugin, execute_plugin, get_all_plugins

router = APIRouter()


class PluginRequest(BaseModel):
    message: str
    force_plugin: Optional[str] = None


@router.post("/api/plugin/run")
async def run_plugin(request: PluginRequest):
    """根据消息自动匹配插件并执行"""
    if request.force_plugin:
        plugin_name = request.force_plugin
    else:
        plugin_name = match_plugin(request.message)

    if not plugin_name:
        return {"matched": False, "message": "No plugin matched"}

    result = await execute_plugin(plugin_name)
    return {
        "matched": True,
        "plugin": plugin_name,
        "status": result.status,
        "data": result.data,
        "error": result.error,
    }


@router.get("/api/plugin/list")
async def list_plugins():
    """列出所有插件"""
    return {"plugins": get_all_plugins()}