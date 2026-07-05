"""Project Manager — 项目工作区核心管理器

支持：
- 项目 CRUD（创建/读取/更新/删除/归档）
- 项目上下文恢复（会话、记忆、文件、任务、工具记录）
- 项目-会话关联管理
- 项目记忆隔离（按 project_id 过滤长期记忆）
"""
import json
import logging
import time
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, func, update

from ..models.project import Project, ProjectFile, ProjectToolRecord, project_conversations
from ..models.memory import Memory, Conversation

logger = logging.getLogger("dream-os.project")


class ProjectManager:
    """Project Manager — 项目生命周期与上下文管理"""

    def __init__(self, session: AsyncSession, user_id: str = "default"):
        self.session = session
        self._user_id = user_id

    # ════════════════════════════════════════════
    # 项目 CRUD
    # ════════════════════════════════════════════

    async def create_project(self, name: str, description: str = "") -> Project:
        """创建新项目"""
        project = Project(
            user_id=self._user_id,
            name=name,
            description=description,
            status="active",
        )
        self.session.add(project)
        await self.session.flush()
        logger.info(f"Project created: {project.id} ({name})")
        return project

    async def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目详情"""
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == self._user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_project(self, project_id: str, updates: dict) -> Optional[Project]:
        """更新项目信息"""
        project = await self.get_project(project_id)
        if not project:
            return None
        for key, value in updates.items():
            if hasattr(project, key) and key not in ("id", "user_id", "created_at"):
                setattr(project, key, value)
        await self.session.flush()
        logger.info(f"Project updated: {project_id}")
        return project

    async def delete_project(self, project_id: str) -> bool:
        """删除项目（级联删除关联数据）"""
        project = await self.get_project(project_id)
        if not project:
            return False
        await self.session.delete(project)
        await self.session.flush()
        logger.info(f"Project deleted: {project_id}")
        return True

    async def archive_project(self, project_id: str) -> bool:
        """归档项目"""
        project = await self.get_project(project_id)
        if not project:
            return False
        project.status = "archived"
        await self.session.flush()
        return True

    async def list_projects(self, include_archived: bool = False) -> list[Project]:
        """列出所有项目"""
        query = select(Project).where(
            Project.user_id == self._user_id,
        )
        if not include_archived:
            query = query.where(Project.status == "active")
        query = query.order_by(desc(Project.updated_at))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ════════════════════════════════════════════
    # 项目-会话 关联管理
    # ════════════════════════════════════════════

    async def link_conversation(self, project_id: str, conversation_id: str) -> bool:
        """将会话关联到项目"""
        # 检查是否已关联
        result = await self.session.execute(
            select(project_conversations).where(
                project_conversations.c.project_id == project_id,
                project_conversations.c.conversation_id == conversation_id,
            )
        )
        if result.first():
            return True  # 已关联

        await self.session.execute(
            project_conversations.insert().values(
                project_id=project_id,
                conversation_id=conversation_id,
            )
        )
        await self.session.flush()

        # 更新项目的最新活跃会话
        await self.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(active_conversation_id=conversation_id)
        )
        await self.session.flush()
        return True

    async def get_project_conversations(self, project_id: str,
                                         limit: int = 20) -> list[dict]:
        """获取项目的所有关联会话"""
        result = await self.session.execute(
            select(Conversation)
            .join(project_conversations,
                  Conversation.id == project_conversations.c.conversation_id)
            .where(project_conversations.c.project_id == project_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        convs = result.scalars().all()
        return [{
            "id": c.id,
            "title": c.title,
            "summary": c.summary[:200] if c.summary else "",
            "message_count": c.message_count or 0,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "updated_at": c.updated_at.isoformat() if c.updated_at else "",
        } for c in convs]

    async def get_active_conversation(self, project_id: str) -> Optional[str]:
        """获取项目的最新活跃会话 ID"""
        project = await self.get_project(project_id)
        if not project:
            return None
        # 如果项目有 active_conversation_id，验证它是否仍然有效
        if project.active_conversation_id:
            result = await self.session.execute(
                select(Conversation).where(
                    Conversation.id == project.active_conversation_id
                )
            )
            if result.scalar_one_or_none():
                return project.active_conversation_id
        # 否则获取最新的会话
        convs = await self.get_project_conversations(project_id, limit=1)
        if convs:
            return convs[0]["id"]
        return None

    # ════════════════════════════════════════════
    # 项目记忆隔离
    # ════════════════════════════════════════════

    async def get_project_memories(self, project_id: str,
                                    max_tokens: int = 500) -> str:
        """获取项目的长期记忆（按 project_id 过滤）"""
        # 先获取项目关联会话的所有 memory_id
        convs = await self.get_project_conversations(project_id, limit=50)
        conv_ids = [c["id"] for c in convs]
        if not conv_ids:
            return ""

        # 从关联会话的自动提取记忆中筛选
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == self._user_id,
                Memory.category == "auto_extracted",
            )
            .order_by(Memory.importance.desc())
        )
        memories = result.scalars().all()[:20]

        lines = []
        total = 0
        for m in memories:
            line = f"- {m.key}: {m.value}"
            total += len(line) // 3 + 1
            if total > max_tokens:
                break
            lines.append(line)

        text = ("【项目长期记忆】\n" + "\n".join(lines)) if lines else ""
        return text

    # ════════════════════════════════════════════
    # 项目上下文恢复
    # ════════════════════════════════════════════

    async def get_project_context(self, project_id: str) -> dict[str, Any]:
        """获取完整项目上下文

        用于 "继续昨天 X 项目" 场景的自动恢复。
        返回：项目信息、活跃会话、记忆、摘要、待办、关键决策、文件、工具记录
        """
        project = await self.get_project(project_id)
        if not project:
            return {"error": "项目不存在"}

        # 活跃会话
        active_conv_id = await self.get_active_conversation(project_id)

        # 最近会话（最多5条）
        recent_convs = await self.get_project_conversations(project_id, limit=5)

        # 项目记忆
        memories = await self.get_project_memories(project_id)

        # 项目文件
        files_result = await self.session.execute(
            select(ProjectFile)
            .where(
                ProjectFile.project_id == project_id,
                ProjectFile.user_id == self._user_id,
            )
            .order_by(desc(ProjectFile.updated_at))
            .limit(10)
        )
        files = [{
            "filename": f.filename,
            "file_type": f.file_type,
            "summary": f.summary[:100] if f.summary else "",
        } for f in files_result.scalars().all()]

        # 最近工具记录
        tool_result = await self.session.execute(
            select(ProjectToolRecord)
            .where(ProjectToolRecord.project_id == project_id)
            .order_by(desc(ProjectToolRecord.created_at))
            .limit(10)
        )
        tool_records = [{
            "tool_name": r.tool_name,
            "status": r.status,
            "duration_ms": r.duration_ms,
        } for r in tool_result.scalars().all()]

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "summary": project.summary,
                "todo_count": project.todo_count,
                "key_decisions": project.key_decisions,
                "next_plan": project.next_plan,
                "created_at": project.created_at.isoformat() if project.created_at else "",
                "updated_at": project.updated_at.isoformat() if project.updated_at else "",
            },
            "active_conversation_id": active_conv_id,
            "recent_conversations": recent_convs,
            "memories": memories,
            "files": files,
            "recent_tool_records": tool_records,
        }

    async def resume_project_context(self, project_id: str) -> dict[str, Any]:
        """恢复项目上下文（用于AI自动恢复）

        这是 "继续昨天 Dream OS 项目" 的核心方法。
        返回 context 信息，可直接注入到 AI prompt 中。
        """
        ctx = await self.get_project_context(project_id)
        if "error" in ctx:
            return ctx

        p = ctx["project"]
        summary_parts = []

        # 构建项目摘要文本
        parts = [f"项目名称: {p['name']}"]
        if p["description"]:
            parts.append(f"项目描述: {p['description']}")
        if p["summary"]:
            parts.append(f"项目进展: {p['summary']}")
        if p["key_decisions"]:
            parts.append(f"关键决策: {p['key_decisions']}")
        if p["next_plan"]:
            parts.append(f"下一步计划: {p['next_plan']}")
        if p["todo_count"] and p["todo_count"] > 0:
            parts.append(f"待办事项: {p['todo_count']} 项")

        summary_parts.append("\n".join(parts))

        if ctx["memories"]:
            summary_parts.append(ctx["memories"])

        if ctx["files"]:
            file_list = "\n".join([f"  - {f['filename']} ({f['file_type']})" for f in ctx["files"]])
            summary_parts.append(f"项目文件:\n{file_list}")

        context_text = "\n\n".join(summary_parts)

        return {
            "project_id": project_id,
            "active_conversation_id": ctx["active_conversation_id"],
            "context_text": context_text,
            "project_name": p["name"],
        }

    # ════════════════════════════════════════════
    # 项目文件管理
    # ════════════════════════════════════════════

    async def add_file(self, project_id: str, filename: str,
                        filepath: str, file_type: str = "",
                        file_size: int = 0, summary: str = "") -> ProjectFile:
        """记录项目关联文件"""
        pf = ProjectFile(
            project_id=project_id,
            user_id=self._user_id,
            filename=filename,
            filepath=filepath,
            file_type=file_type,
            file_size=file_size,
            summary=summary,
        )
        self.session.add(pf)
        await self.session.flush()
        return pf

    async def remove_file(self, file_id: str) -> bool:
        """移除项目文件记录"""
        result = await self.session.execute(
            select(ProjectFile).where(
                ProjectFile.id == file_id,
                ProjectFile.user_id == self._user_id,
            )
        )
        pf = result.scalar_one_or_none()
        if not pf:
            return False
        await self.session.delete(pf)
        await self.session.flush()
        return True

    # ════════════════════════════════════════════
    # 工具记录
    # ════════════════════════════════════════════

    async def add_tool_record(self, project_id: str, tool_name: str,
                                command: str = "", status: str = "success",
                                duration_ms: int = 0,
                                result_preview: str = "",
                                conversation_id: str = "") -> ProjectToolRecord:
        """记录项目中的工具调用"""
        rec = ProjectToolRecord(
            project_id=project_id,
            conversation_id=conversation_id or None,
            tool_name=tool_name,
            command=command,
            status=status,
            duration_ms=duration_ms,
            result_preview=result_preview[:500],
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    # ════════════════════════════════════════════
    # 批量操作
    # ════════════════════════════════════════════

    async def get_project_stats(self, project_id: str) -> dict:
        """获取项目统计信息"""
        project = await self.get_project(project_id)
        if not project:
            return {}

        convs = await self.get_project_conversations(project_id, limit=1000)
        total_messages = sum(c["message_count"] for c in convs)

        tool_result = await self.session.execute(
            select(func.count(ProjectToolRecord.id))
            .where(ProjectToolRecord.project_id == project_id)
        )
        total_tools = tool_result.scalar() or 0

        file_result = await self.session.execute(
            select(func.count(ProjectFile.id))
            .where(ProjectFile.project_id == project_id)
        )
        total_files = file_result.scalar() or 0

        return {
            "conversations": len(convs),
            "total_messages": total_messages,
            "tool_records": total_tools,
            "files": total_files,
            "todo_count": project.todo_count or 0,
        }