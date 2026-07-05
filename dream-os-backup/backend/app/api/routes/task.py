"""任务 API 路由 — ReAct Agent 模式"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.session import get_db, async_session_factory
from ...models.task import Task
from ...core.agent_loop import AgentLoop, signal_confirmation
from pydantic import BaseModel

logger = logging.getLogger("dream-os")


class ConfirmRequest(BaseModel):
    confirm: bool

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    input: str


async def run_agent(task_id: str):
    """后台执行 ReAct Agent"""
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            agent = AgentLoop()
            await agent.run(task, db)
            await db.commit()
    except Exception as e:
        logger.exception(f"Agent task {task_id} failed: {e}")
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)[:1000]
                    await db.commit()
        except Exception as e2:
            logger.exception(f"Failed to update task status: {e2}")


@router.post("")
async def create_task(
    req: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """创建任务并启动 ReAct Agent 后台执行"""
    task = Task(user_input=req.input)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 后台启动 ReAct Agent
    background_tasks.add_task(run_agent, task.id)
    logger.info(f"Task {task.id} created, agent queued")

    return {
        "task_id": task.id,
        "status": task.status,
        "message": "ReAct Agent 已启动...",
    }


@router.get("")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    """获取任务列表"""
    result = await db.execute(
        select(Task).order_by(Task.created_at.desc()).limit(50)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "user_input": t.user_input,
            "status": t.status,
            "result": t.result,
            "plan": t.plan,
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in tasks
    ]


@router.get("/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个任务详情"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "id": task.id,
        "user_input": task.user_input,
        "status": task.status,
        "result": task.result,
        "plan": task.plan,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取任务日志"""
    from ...logger import TaskLogger
    logger = TaskLogger(task_id, db)
    return await logger.get_logs()


@router.post("/{task_id}/confirm")
async def confirm_task(task_id: str, req: ConfirmRequest):
    """用户确认/拒绝 DANGEROUS 操作"""
    signal_confirmation(task_id, req.confirm)
    return {
        "task_id": task_id,
        "confirmed": req.confirm,
        "message": "已确认执行" if req.confirm else "已拒绝操作",
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """删除任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    await db.delete(task)
    await db.commit()
    return {"message": "任务已删除"}
