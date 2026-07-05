"""WebSocket 处理"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.session import get_db, async_session_factory
from ..models.task import Task
from ..core.agent_loop import AgentLoop

router = APIRouter()

# 存储活跃的 WebSocket 连接
active_ws: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/tasks/{task_id}")
async def ws_task(task_id: str, websocket: WebSocket):
    """实时任务进度推送 — ReAct Agent"""
    await websocket.accept()

    if task_id not in active_ws:
        active_ws[task_id] = []
    active_ws[task_id].append(websocket)

    try:
        db = async_session_factory()
        try:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()

            if task and task.status == "pending":
                agent = AgentLoop()

                async def ws_send(data):
                    for ws in active_ws.get(task_id, []):
                        try:
                            await ws.send_text(data)
                        except Exception:
                            pass

                try:
                    await agent.run(task, db, ws_send)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    for ws in active_ws.get(task_id, []):
                        try:
                            await ws.send_text(json.dumps({
                                "type": "error",
                                "message": str(e),
                            }, ensure_ascii=False))
                        except Exception:
                            pass
                finally:
                    await db.close()

            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({"type": "ping"}))
        finally:
            pass
    except WebSocketDisconnect:
        pass
    finally:
        if task_id in active_ws:
            active_ws[task_id].remove(websocket)
