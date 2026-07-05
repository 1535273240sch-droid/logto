"""V3 自主开发 API — SSE 流式接口

POST /api/v3/dev/start
  用户提交开发需求，Dream OS 自主完成完整开发流程。
  通过 SSE 实时推送 8 个 Agent 的工作状态。

GET /api/v3/dev/tasks
  列出所有开发任务

GET /api/v3/dev/tasks/{task_id}
  获取开发任务详情

GET /api/v3/dev/tasks/{task_id}/files
  获取任务工作空间文件列表

GET /api/v3/dev/tasks/{task_id}/files/{filepath}
  获取工作空间文件内容
"""
import json
import uuid
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models.dev_task import DevTask
from ...tools import ToolManager, ShellTool, FileTool, HttpTool
from ...core.v3 import AutoLoop, SSEv2
from ...core.v3.blackboard import SharedBlackboard

logger = logging.getLogger("dream-os.v3.api")
router = APIRouter(prefix="/api/v3/dev", tags=["v3-dev"])


# ── 全局 ToolManager (V3 共享) ──
_v3_tool_manager: ToolManager | None = None

def get_v3_tool_manager() -> ToolManager:
    global _v3_tool_manager
    if _v3_tool_manager is None:
        _v3_tool_manager = ToolManager()
        _v3_tool_manager.register(ShellTool())
        _v3_tool_manager.register(FileTool())
        _v3_tool_manager.register(HttpTool())
    return _v3_tool_manager


# ── 请求模型 ──

class DevRequest(BaseModel):
    requirement: str
    project_id: Optional[str] = None
    max_iterations: int = 3


# ── 路由 ──

@router.post("/start")
async def start_dev(req: DevRequest, db: AsyncSession = Depends(get_db)):
    """启动自主开发任务 — SSE 流式返回"""
    task_id = str(uuid.uuid4())[:8]

    # 创建 DB 记录
    dev_task = DevTask(
        id=task_id,
        requirement=req.requirement,
        status="pending",
        max_iterations=req.max_iterations,
        project_id=req.project_id,
    )
    db.add(dev_task)
    await db.commit()

    # 使用 asyncio.Queue 桥接 emit 回调和 SSE 生成器
    event_queue: asyncio.Queue = asyncio.Queue()

    async def gen():
        # 在后台运行自主开发循环
        async def run_dev():
            try:
                dev_task.status = "planning"
                dev_task.workspace_path = f"/workspace/projects/{task_id}"
                await db.commit()

                tool_manager = get_v3_tool_manager()
                auto_loop = AutoLoop(tool_manager)

                # SSE 事件回调 — 将事件放入队列
                async def emit(event: dict):
                    # 更新 DB
                    try:
                        if event.get("type") == "agent_start":
                            dev_task.current_agent = event.get("agent", "")
                            dev_task.status = event.get("agent", "running")
                            await db.commit()

                        if event.get("type") == "agent_tool_call":
                            dev_task.execution_log = (dev_task.execution_log or []) + [{
                                "agent": event.get("agent"),
                                "tool": event.get("tool"),
                                "arguments": event.get("arguments"),
                                "iteration": event.get("iteration"),
                                "timestamp": datetime.now().isoformat(),
                            }]
                            await db.commit()

                        if event.get("type") == "agent_complete":
                            bb = auto_loop.get_blackboard()
                            dev_task.plan = bb.plan
                            dev_task.architecture = bb.architecture
                            dev_task.files = list(bb.files.keys())
                            dev_task.test_results = bb.test_results
                            dev_task.deployment = bb.deployment
                            dev_task.reports = bb.reports
                            dev_task.iteration = bb.iteration
                            await db.commit()
                    except Exception:
                        pass

                    # 将 SSE 事件放入队列
                    await event_queue.put(SSEv2._format(event))

                # 运行自主开发循环
                result = await auto_loop.run(
                    requirement=req.requirement,
                    task_id=task_id,
                    emit=emit,
                    max_iterations=req.max_iterations,
                )

                # 更新最终状态
                dev_task.status = "completed" if result["success"] else "failed"
                dev_task.result = result.get("summary", "")
                dev_task.summary = result.get("summary", "")
                dev_task.completed_at = datetime.utcnow()
                await db.commit()

            except Exception as e:
                logger.error(f"Dev task {task_id} failed: {e}", exc_info=True)
                dev_task.status = "failed"
                dev_task.error_log = str(e)
                await db.commit()
                await event_queue.put(SSEv2.error(str(e)))

            finally:
                await event_queue.put(None)  # 结束信号

        # 启动后台任务
        task = asyncio.create_task(run_dev())

        # 从队列读取并 yield SSE 事件
        try:
            while True:
                event_data = await event_queue.get()
                if event_data is None:
                    break
                yield event_data
        finally:
            if not task.done():
                task.cancel()
            yield SSEv2.done()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/tasks")
async def list_dev_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(20),
    db: AsyncSession = Depends(get_db),
):
    """列出开发任务"""
    query = select(DevTask).order_by(desc(DevTask.created_at)).limit(limit)
    if status:
        query = query.where(DevTask.status == status)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "id": t.id,
                "requirement": t.requirement[:100],
                "status": t.status,
                "current_agent": t.current_agent,
                "iteration": t.iteration,
                "max_iterations": t.max_iterations,
                "files_count": len(t.files) if t.files else 0,
                "summary": t.summary[:200] if t.summary else "",
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "completed_at": t.completed_at.isoformat() if t.completed_at else "",
            }
            for t in tasks
        ],
        "count": len(tasks),
    }


@router.get("/tasks/{task_id}")
async def get_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取开发任务详情"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})

    return {
        "id": task.id,
        "requirement": task.requirement,
        "status": task.status,
        "current_agent": task.current_agent,
        "workspace_path": task.workspace_path,
        "plan": task.plan,
        "architecture": task.architecture,
        "files": task.files,
        "test_results": task.test_results,
        "deployment": task.deployment,
        "reports": task.reports,
        "execution_log": (task.execution_log or [])[-20:],  # 最近20条
        "iteration": task.iteration,
        "max_iterations": task.max_iterations,
        "summary": task.summary,
        "error_log": task.error_log,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "completed_at": task.completed_at.isoformat() if task.completed_at else "",
    }


@router.get("/tasks/{task_id}/files")
async def get_task_files(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取任务工作空间文件列表"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})

    from ...core.v3.workspace import Workspace
    ws = Workspace(task_id)
    if not ws.exists():
        return {"files": [], "workspace": task.workspace_path}

    files = ws.list_files()
    return {
        "files": files,
        "workspace": task.workspace_path,
        "file_tree": ws.file_tree(),
    }


@router.get("/tasks/{task_id}/files/{filepath:path}")
async def get_task_file_content(task_id: str, filepath: str, db: AsyncSession = Depends(get_db)):
    """获取工作空间文件内容"""
    from ...core.v3.workspace import Workspace
    ws = Workspace(task_id)
    if not ws.exists():
        return JSONResponse(status_code=404, content={"error": "工作空间不存在"})

    content = ws.read_file(filepath)
    if not content:
        # 尝试从 root 读取
        import os
        full_path = os.path.join(ws.root, filepath)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            return JSONResponse(status_code=404, content={"error": "文件不存在"})

    return {
        "filepath": filepath,
        "content": content[:10000],  # 限制10K
        "size": len(content),
    }


@router.get("/agents")
async def list_agents():
    """列出所有 V3 Agent 信息"""
    from ...core.v3.agents import ALL_AGENTS
    agents = []
    for agent_cls in ALL_AGENTS:
        agent = agent_cls()
        agents.append(agent.to_info())
    return {"agents": agents, "count": len(agents)}
