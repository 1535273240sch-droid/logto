"""Tool Center API 路由

提供工具配置管理、执行历史查询、健康监控和自动发现能力。
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...core.tool_center import get_tool_center

logger = logging.getLogger("dream-os.tool_center")
router = APIRouter(prefix="/api/tool-center", tags=["tool-center"])


# ── 请求模型 ──

class UpdateConfigRequest(BaseModel):
    timeout: Optional[int] = None
    retry_count: Optional[int] = None
    security_level: Optional[str] = None
    enabled: Optional[bool] = None


class TestToolRequest(BaseModel):
    command: str = ""


# ── 工具列表（含配置 + 健康状态） ──

@router.get("/tools")
async def list_tools():
    """获取所有工具详情（含配置和健康状态）"""
    tc = get_tool_center()
    return {
        "tools": tc.list_configs(),
        "count": len(tc.list_configs()),
    }


# ── 工具配置更新 ──

@router.get("/tools/{name}")
async def get_tool(name: str):
    """获取单个工具详情"""
    tc = get_tool_center()
    configs = tc.list_configs()
    for c in configs:
        if c["name"] == name:
            return c
    raise HTTPException(status_code=404, detail=f"工具 '{name}' 未找到")


@router.put("/tools/{name}")
async def update_tool_config(name: str, req: UpdateConfigRequest):
    """更新工具配置（超时、重试、安全级别、启用/禁用）"""
    tc = get_tool_center()
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    cfg = tc.update_config(name, updates)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"工具 '{name}' 未找到")

    return {"status": "ok", "tool": cfg.to_dict()}


# ── 执行历史 ──

@router.get("/history")
async def get_history(limit: int = 50):
    """获取最近工具执行历史"""
    tc = get_tool_center()
    return {"records": tc.get_history(limit), "count": min(limit, tc.history.count)}


@router.get("/tools/{name}/history")
async def get_tool_history(name: str, limit: int = 20):
    """获取指定工具的执行历史"""
    tc = get_tool_center()
    return {"tool": name, "records": tc.get_tool_history(name, limit)}


# ── 健康状态 ──

@router.get("/status")
async def get_status():
    """获取所有工具的健康状态摘要"""
    tc = get_tool_center()
    return tc.get_health_summary()


# ── 仪表盘 ──

@router.get("/dashboard")
async def get_dashboard():
    """获取 Tool Center 完整仪表盘数据"""
    tc = get_tool_center()
    return tc.get_dashboard()


# ── 测试工具 ──

@router.post("/tools/{name}/test")
async def test_tool(name: str, req: TestToolRequest = TestToolRequest()):
    """测试指定工具的运行状态"""
    tc = get_tool_center()
    record = await tc.test_tool(name, req.command)
    return {
        "status": "ok",
        "result": {
            "tool": record.tool_name,
            "status": record.status,
            "duration_ms": record.duration_ms,
            "result_preview": record.result[:300],
            "error": record.error[:200] if record.error else "",
        },
    }


# ── 自动发现 ──

@router.post("/discover")
async def discover_tools():
    """触发自动发现，注册新工具"""
    tc = get_tool_center()
    discovered = tc.discover()
    return {
        "status": "ok",
        "discovered": discovered,
        "count": len(discovered),
    }