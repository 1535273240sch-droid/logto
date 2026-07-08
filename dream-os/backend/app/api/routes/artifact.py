"""Artifact API 路由 — 成果物管理"""
import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("dream-os.artifact")
router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class GenerateRequest(BaseModel):
    content: str
    artifact_types: list[str] = []
    title: str = ""
    conversation_id: str = ""
    project_id: str = ""


@router.get("")
async def list_artifacts(conversation_id: str = "", project_id: str = ""):
    """列出成果物"""
    from ...core.artifact_engine import artifact_engine
    # 如果注册表为空但磁盘有文件，触发恢复
    if not artifact_engine._registry:
        artifact_engine._restore_from_disk()
    artifacts = artifact_engine.list_artifacts(conversation_id, project_id)
    return {
        "artifacts": [a.to_dict() for a in artifacts],
        "count": len(artifacts),
    }


@router.get("/types")
async def list_supported_types():
    """列出支持的成果物类型"""
    from ...core.artifact_engine import artifact_engine
    types = artifact_engine.list_supported_types()
    return {"types": types, "count": len(types)}


@router.post("/generate")
async def generate_artifact(req: GenerateRequest):
    """手动生成成果物"""
    from ...core.artifact_engine import artifact_engine
    from ...core.output_router import output_router

    if req.artifact_types:
        # 指定类型生成
        results = []
        for atype in req.artifact_types:
            artifact = await artifact_engine.generate(
                artifact_type=atype,
                content=req.content,
                title=req.title,
                conversation_id=req.conversation_id,
                project_id=req.project_id,
            )
            results.append(artifact.to_dict())
        return {"artifacts": results, "count": len(results)}
    else:
        # 自动路由
        plan = output_router.route(req.content)
        artifacts = await artifact_engine.generate_batch(
            plan.to_dict(), req.content,
            conversation_id=req.conversation_id,
            project_id=req.project_id,
        )
        return {
            "artifacts": [a.to_dict() for a in artifacts],
            "plan": plan.to_dict(),
            "count": len(artifacts),
        }


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str):
    """获取成果物详情"""
    from ...core.artifact_engine import artifact_engine
    artifact = artifact_engine.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="成果物不存在")
    return artifact.to_dict()


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    """下载成果物文件"""
    from ...core.artifact_engine import artifact_engine, ARTIFACT_DIR
    artifact = artifact_engine.get_artifact(artifact_id)
    if artifact and artifact.filepath and os.path.exists(artifact.filepath):
        return FileResponse(
            artifact.filepath,
            filename=artifact.filename,
            media_type="application/octet-stream",
        )
    # 兜底：从磁盘按 ID 前缀匹配文件
    if ARTIFACT_DIR.exists():
        for f in ARTIFACT_DIR.iterdir():
            if f.is_file() and f.name.startswith(artifact_id + "_"):
                # 恢复注册
                from ...core.artifact_engine import Artifact
                parts = f.name.split('_', 1)
                title = parts[1].rsplit('.', 1)[0] if len(parts) > 1 else f.name
                restored = Artifact(
                    id=artifact_id,
                    filename=f.name,
                    artifact_type="unknown",
                    title=title,
                    filepath=str(f),
                    file_size=f.stat().st_size,
                    status="completed",
                )
                artifact_engine._registry[artifact_id] = restored
                return FileResponse(
                    str(f),
                    filename=f.name,
                    media_type="application/octet-stream",
                )
    raise HTTPException(status_code=404, detail="成果物文件不存在")


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """删除成果物"""
    from ...core.artifact_engine import artifact_engine
    ok = artifact_engine.delete_artifact(artifact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="成果物不存在")
    return {"status": "ok", "deleted": True}
