"""Agent API 路由"""
from fastapi import APIRouter
from ...agents.server import ServerAgent

router = APIRouter(prefix="/api/agents", tags=["agents"])

agent = ServerAgent()


@router.get("")
async def list_agents():
    """获取 Agent 列表"""
    return {
        "agents": [agent.to_info()],
        "count": 1,
    }


@router.get("/{name}")
async def get_agent(name: str):
    """获取单个 Agent 状态"""
    if name == agent.name:
        return agent.to_info()
    return {"error": f"Agent '{name}' 不存在"}
