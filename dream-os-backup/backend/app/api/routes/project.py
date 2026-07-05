"""Project API 路由 — 项目工作区 CRUD + 上下文管理"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...core.project_manager import ProjectManager

logger = logging.getLogger("dream-os.project")
router = APIRouter(prefix="/api/projects", tags=["projects"])


# ── 请求/响应模型 ──

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    todo_count: Optional[int] = None
    key_decisions: Optional[str] = None
    next_plan: Optional[str] = None
    status: Optional[str] = None


# ── 依赖注入 ──

async def get_pm(db: AsyncSession = Depends(get_db)):
    return ProjectManager(db)


# ── CRUD 端点 ──

@router.post("")
async def create_project(req: CreateProjectRequest, pm: ProjectManager = Depends(get_pm)):
    """创建新项目"""
    project = await pm.create_project(req.name, req.description)
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else "",
    }


@router.get("")
async def list_projects(include_archived: bool = False,
                        pm: ProjectManager = Depends(get_pm)):
    """列出所有项目"""
    projects = await pm.list_projects(include_archived)
    return {
        "projects": [{
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "status": p.status,
            "summary": p.summary[:100] if p.summary else "",
            "todo_count": p.todo_count or 0,
            "active_conversation_id": p.active_conversation_id,
            "created_at": p.created_at.isoformat() if p.created_at else "",
            "updated_at": p.updated_at.isoformat() if p.updated_at else "",
        } for p in projects],
        "count": len(projects),
    }


@router.get("/{project_id}")
async def get_project(project_id: str, pm: ProjectManager = Depends(get_pm)):
    """获取项目详情（含完整上下文）"""
    project = await pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    ctx = await pm.get_project_context(project_id)
    stats = await pm.get_project_stats(project_id)
    ctx["stats"] = stats
    return ctx


@router.put("/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest,
                          pm: ProjectManager = Depends(get_pm)):
    """更新项目信息"""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    project = await pm.update_project(project_id, updates)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {"status": "ok", "project_id": project.id, "name": project.name}


@router.delete("/{project_id}")
async def delete_project(project_id: str, pm: ProjectManager = Depends(get_pm)):
    """删除项目"""
    ok = await pm.delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"status": "ok", "deleted": True}


@router.post("/{project_id}/archive")
async def archive_project(project_id: str, pm: ProjectManager = Depends(get_pm)):
    """归档项目"""
    ok = await pm.archive_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"status": "ok", "archived": True}


# ── 上下文管理 ──

@router.get("/{project_id}/context")
async def get_context(project_id: str, pm: ProjectManager = Depends(get_pm)):
    """获取项目上下文（用于AI自动恢复）"""
    ctx = await pm.resume_project_context(project_id)
    if "error" in ctx:
        raise HTTPException(status_code=404, detail=ctx["error"])
    return ctx


@router.get("/{project_id}/conversations")
async def get_conversations(project_id: str, limit: int = 20,
                             pm: ProjectManager = Depends(get_pm)):
    """获取项目的关联会话列表"""
    convs = await pm.get_project_conversations(project_id, limit)
    return {"conversations": convs, "count": len(convs)}


@router.get("/{project_id}/stats")
async def get_stats(project_id: str, pm: ProjectManager = Depends(get_pm)):
    """获取项目统计信息"""
    stats = await pm.get_project_stats(project_id)
    if not stats:
        raise HTTPException(status_code=404, detail="项目不存在")
    return stats


# ── 项目快速搜索 ──

@router.get("/search/{keyword}")
async def search_projects(keyword: str, pm: ProjectManager = Depends(get_pm)):
    """按关键词搜索项目"""
    projects = await pm.list_projects()
    keyword_lower = keyword.lower()
    matched = [p for p in projects
               if keyword_lower in p.name.lower()
               or keyword_lower in (p.description or "").lower()]
    return {
        "projects": [{
            "id": p.id,
            "name": p.name,
            "description": p.description[:100] if p.description else "",
            "status": p.status,
        } for p in matched],
        "count": len(matched),
    }