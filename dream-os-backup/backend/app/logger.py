"""Logger - 结构化任务日志记录"""
import json
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from .models.log import Log

logger = logging.getLogger("dream-os")


class TaskLogger:
    """任务执行日志管理器"""

    def __init__(self, task_id: str, db: AsyncSession):
        self.task_id = task_id
        self.db = db

    async def log(
        self,
        step_id: int,
        step_name: str,
        agent: str,
        tool: str,
        command: str,
        duration_ms: int,
        exit_code: int,
        stdout: str,
        stderr: str,
        success: bool,
    ) -> Log:
        log_entry = Log(
            task_id=self.task_id,
            step_id=step_id,
            step_name=step_name,
            agent=agent,
            tool=tool,
            command=command,
            duration_ms=duration_ms,
            exit_code=exit_code,
            stdout=stdout[:10000] if stdout else None,
            stderr=stderr[:5000] if stderr else None,
            status="success" if success else "failed",
        )
        self.db.add(log_entry)
        await self.db.flush()

        logger.info(
            f"[Task:{self.task_id[:8]}] Step {step_id}: {step_name} "
            f"({tool}) - {'✓' if success else '✗'} ({duration_ms}ms)"
        )
        return log_entry

    async def get_logs(self) -> list[dict]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(Log)
            .where(Log.task_id == self.task_id)
            .order_by(Log.step_id)
        )
        logs = result.scalars().all()
        return [
            {
                "step_id": l.step_id,
                "step_name": l.step_name,
                "agent": l.agent,
                "tool": l.tool,
                "command": l.command,
                "duration_ms": l.duration_ms,
                "exit_code": l.exit_code,
                "stdout": l.stdout,
                "stderr": l.stderr,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
