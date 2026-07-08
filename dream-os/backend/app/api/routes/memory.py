"""记忆 API 路由 — V1.5 智能上下文记忆系统

API 端点：
  GET    /api/memory              → 获取所有长期记忆
  POST   /api/memory/update       → 更新长期记忆
  DELETE /api/memory/{key}        → 删除长期记忆
  GET    /api/conversation        → 获取当前会话
  POST   /api/conversation        → 创建新会话
  GET    /api/conversation/summary      → 获取会话摘要
  POST   /api/conversation/summarize    → 手动触发摘要生成
  GET    /api/conversation/messages     → 获取会话消息列表
  POST   /api/conversation/message      → 添加消息到会话
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from ...db.session import get_db
from ...core.memory import ContextMemoryManager

router = APIRouter(prefix="/api", tags=["memory"])


# ── 请求/响应模型 ──────────────────────────────

class MemoryUpdateRequest(BaseModel):
    key: str
    value: str
    category: str = "general"
    importance: int = 5


class ConversationCreateRequest(BaseModel):
    title: str = "新对话"
    user_id: str = "default"


class MessageAddRequest(BaseModel):
    conversation_id: Optional[str] = None
    role: str = "user"
    content: str = ""


class SummarizeRequest(BaseModel):
    conversation_id: Optional[str] = None


# ── 长期记忆 API ──────────────────────────────

@router.get("/memory")
async def get_memories(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取所有长期记忆"""
    mm = ContextMemoryManager(db)
    memories = await mm.get_all_memories()

    if category:
        memories = {
            k: v for k, v in memories.items()
            if v.get("category") == category
        }

    return {"memories": memories, "count": len(memories)}


@router.post("/memory/update")
async def update_memory(
    req: MemoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新长期记忆"""
    mm = ContextMemoryManager(db)
    await mm.set_memory(req.key, req.value, req.category, req.importance)
    await db.commit()
    return {
        "message": "记忆已保存",
        "key": req.key,
        "importance": req.importance,
    }


@router.delete("/memory/{key}")
async def delete_memory(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """删除长期记忆"""
    mm = ContextMemoryManager(db)
    deleted = await mm.delete_memory(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="记忆不存在")
    await db.commit()
    return {"message": "记忆已删除", "key": key}


# ── 会话 API ──────────────────────────────

@router.get("/conversation")
async def get_conversation(
    conversation_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取当前会话信息"""
    mm = ContextMemoryManager(db)
    conv = await mm.get_or_create_conversation(conversation_id)
    return {
        "id": conv.id,
        "title": conv.title,
        "summary": conv.summary or "",
        "message_count": conv.message_count or 0,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


@router.post("/conversation")
async def create_conversation(
    req: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    mm = ContextMemoryManager(db)
    from ...models.memory import Conversation as ConvModel
    conv = ConvModel(user_id=req.user_id, title=req.title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "message_count": 0,
    }


@router.get("/conversation/summary")
async def get_conversation_summary(
    conversation_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取会话摘要"""
    mm = ContextMemoryManager(db, conversation_id=conversation_id)
    summary = await mm.get_summary()
    conv = await mm.get_conversation()
    return {
        "conversation_id": conv.id if conv else None,
        "summary": summary or "",
        "summary_token_count": conv.summary_token_count if conv else 0,
    }


@router.post("/conversation/summarize")
async def summarize_conversation(
    req: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动触发会话摘要生成（需要 AI 回调，返回可用的 AI 摘要函数）"""
    from ...core.ai_provider import get_ai_client

    mm = ContextMemoryManager(db, conversation_id=req.conversation_id)
    conv = await mm.get_or_create_conversation()

    # 获取所有消息
    from sqlalchemy import select
    from ...models.memory import Message
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    all_messages = list(result.scalars().all())

    if not all_messages:
        return {"message": "会话为空，无需摘要", "summary": conv.summary or ""}

    # 构建摘要用的完整对话文本
    conversation_text = "\n".join([
        f"[{m.role.upper()}] {m.content[:1000]}"
        for m in all_messages
    ])

    # 调用 AI 生成摘要
    try:
        client, model = await get_ai_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个高效的对话摘要助手。请用简洁的语言总结这段对话的核心内容、已完成的动作、用户的关键信息和待办事项。控制在300字以内。"},
                {"role": "user", "content": f"请总结以下对话：\n\n{conversation_text[:8000]}"},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        new_summary = response.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 摘要生成失败: {str(e)}")

    # 合并旧摘要
    old_summary = conv.summary or ""
    if old_summary:
        new_summary = f"【历史摘要】{old_summary}\n【新对话】{new_summary}"

    await mm.update_summary(new_summary)
    await db.commit()

    return {
        "message": "摘要已生成",
        "summary": new_summary,
        "message_count": len(all_messages),
    }


@router.get("/conversation/messages")
async def get_conversation_messages(
    conversation_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取会话消息列表"""
    mm = ContextMemoryManager(db, conversation_id=conversation_id)
    conv = await mm.get_or_create_conversation()

    from sqlalchemy import select, desc
    from ...models.memory import Message
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()

    return {
        "conversation_id": conv.id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content[:2000],
                "token_count": m.token_count or 0,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "total": len(messages),
    }


@router.post("/conversation/message")
async def add_conversation_message(
    req: MessageAddRequest,
    db: AsyncSession = Depends(get_db),
):
    """添加消息到会话（可用于外部系统写入消息）"""
    mm = ContextMemoryManager(db, conversation_id=req.conversation_id)
    msg = await mm.add_message(req.role, req.content)

    # 自动提取长期记忆（仅 user 角色）
    extracted = []
    if req.role == "user":
        extracted = await mm.extract_memories_from_message(req.content)

    await db.commit()

    return {
        "message_id": msg.id,
        "conversation_id": mm.conversation_id,
        "role": msg.role,
        "token_count": msg.token_count or 0,
        "extracted_memories": extracted,
    }