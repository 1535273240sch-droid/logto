"""流式对话 API V2 — Agent Pipeline 完整闭环

增强 SSE 事件协议，支持 AI 工作状态可视化。
每个 Pipeline Step 发射 step_start + step_complete 事件对，
前端可实时展示步骤流转、工具执行状态和耗时。
"""
import json
import asyncio
import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.session import get_db
from ...core.agent_pipeline import AgentPipeline
from ...core.tool_registry import ToolRegistry, ToolStatus
from ...core.ai_provider import get_ai_client
from ...core.events import (
    StepTimer,
    make_step_start, make_step_complete,
    make_pipeline_start, make_done, make_error,
    make_tool_start, make_tool_result,
    make_content, make_intent_event,
    make_plan_event, make_tools_event,
)

logger = logging.getLogger("dream-os")
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: List[Dict] = []
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None  # 项目工作区支持


# 全局 ToolRegistry
_registry = None
def get_registry():
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def _gen_event(event_data: str):
    """便捷包装：yield SSE 事件"""
    return event_data


# ════════════════════════════════════════════════════════════════
# V3 自主开发任务识别 (聊天入口自动路由)
# ════════════════════════════════════════════════════════════════

# 大型开发任务关键词 (命中即触发自主开发模式)
_DEV_KEYWORDS = [
    "开发一个", "开发一个网站", "开发一个 app", "开发一个应用",
    "做一个网站", "做一个 app", "做一个应用", "做一个系统",
    "写一个网站", "写一个 app", "写一个项目",
    "帮我开发", "帮我做", "帮我写一个", "帮我部署",
    "构建一个", "搭建一个", "实现一个",
    "量化系统", "量化平台", "股票平台", "电商平台",
    "完整的项目", "完整的网站", "完整的系统", "完整的应用",
    "部署服务器", "部署项目", "部署网站",
    "自主开发", "自动开发",
]

# 简单查询排除词 (即使命中开发关键词也走普通聊天)
_SIMPLE_QUERY_KEYWORDS = [
    "天气", "股票行情", "黄金价格", "你好", "介绍你自己",
    "是什么", "什么是", "怎么样", "多少钱", "解释一下",
    "翻译", "计算", "查询",
]

def _is_dev_task(message: str) -> bool:
    """识别是否为大型自主开发任务"""
    if not message or len(message) < 8:
        return False
    # 排除简单查询
    for kw in _SIMPLE_QUERY_KEYWORDS:
        if kw in message:
            return False
    # 命中开发关键词
    for kw in _DEV_KEYWORDS:
        if kw in message:
            return True
    # 长消息 + 包含"开发/项目/网站/app/系统"任意一个
    if len(message) > 15:
        for kw in ["开发", "项目", "网站", "app", "APP", "系统", "平台", "部署"]:
            if kw in message:
                return True
    return False


async def _run_v3_dev_via_chat(req: ChatRequest, db: AsyncSession):
    """在聊天流中启动 V3 自主开发，桥接 SSE 事件"""
    import uuid
    import asyncio
    from datetime import datetime
    from ...models.dev_task import DevTask
    from ...tools import ToolManager, ShellTool, FileTool, HttpTool
    from ...core.v3 import AutoLoop, SSEv2

    task_id = str(uuid.uuid4())[:8]

    # 创建 DB 记录
    dev_task = DevTask(
        id=task_id,
        requirement=req.requirement if hasattr(req, 'requirement') else req.message,
        status="planning",
        max_iterations=3,
        project_id=req.project_id,
        workspace_path=f"/workspace/projects/{task_id}",
    )
    db.add(dev_task)
    await db.commit()

    requirement = req.message
    event_queue: asyncio.Queue = asyncio.Queue()

    # SSE 事件格式器 — 转换为前端可识别的格式
    def format_sse(event: dict) -> str:
        import json
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def run_dev():
        try:
            # 注册工具
            tm = ToolManager()
            tm.register(ShellTool())
            tm.register(FileTool())
            tm.register(HttpTool())

            auto_loop = AutoLoop(tm)

            # emit 回调 — 桥接 V3 事件到 chat SSE 流
            async def emit(event: dict):
                # 注入 task_id (前端需要)
                event["task_id"] = task_id
                # 持久化到 DB
                try:
                    if event.get("type") == "agent_start":
                        dev_task.current_agent = event.get("agent", "")
                        dev_task.status = "running"
                        await db.commit()
                    elif event.get("type") == "agent_complete":
                        bb = auto_loop.get_blackboard()
                        dev_task.plan = bb.plan
                        dev_task.architecture = bb.architecture
                        dev_task.files = list(bb.files.keys()) if bb.files else []
                        dev_task.test_results = bb.test_results
                        dev_task.deployment = bb.deployment
                        dev_task.reports = bb.reports
                        dev_task.iteration = bb.iteration
                        await db.commit()
                except Exception:
                    pass
                # 推送到 SSE 队列
                await event_queue.put(format_sse(event))

            # 启动自主开发循环
            result = await auto_loop.run(
                requirement=requirement,
                task_id=task_id,
                emit=emit,
                max_iterations=3,
            )

            # 完成事件
            dev_task.status = "completed" if result.get("success") else "failed"
            dev_task.summary = result.get("summary", "")
            dev_task.result = result.get("summary", "")
            dev_task.completed_at = datetime.utcnow()
            await db.commit()

            # 推送完成事件 (含成果物)
            completion_event = {
                "type": "dev_complete",
                "task_id": task_id,
                "success": result.get("success", False),
                "summary": result.get("summary", ""),
                "deployment": dev_task.deployment,
                "files": dev_task.files,
                "reports": dev_task.reports,
            }
            if not result.get("success"):
                completion_event["error"] = result.get("error", "未知错误")
            await event_queue.put(format_sse(completion_event))

        except Exception as e:
            logger.error(f"V3 dev task {task_id} failed: {e}", exc_info=True)
            dev_task.status = "failed"
            dev_task.error_log = str(e)
            await db.commit()
            await event_queue.put(format_sse({
                "type": "error",
                "task_id": task_id,
                "error": str(e),
            }))
        finally:
            await event_queue.put(None)  # 结束信号

    # 启动后台任务
    task = asyncio.create_task(run_dev())

    # 发送 dev_start 事件 (最先推送)
    yield format_sse({
        "type": "dev_start",
        "task_id": task_id,
        "requirement": requirement,
    })

    # 从队列读取并 yield
    try:
        while True:
            event_data = await event_queue.get()
            if event_data is None:
                break
            yield event_data
    finally:
        if not task.done():
            task.cancel()
        yield "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """SSE 流式对话 — 自动识别大型开发任务，融合 V3 自主开发"""

    # ═══ V3 自主开发任务自动识别 ═══
    if _is_dev_task(req.message):
        return StreamingResponse(
            _run_v3_dev_via_chat(req, db),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    registry = get_registry()

    async def gen():
        timer = StepTimer()
        try:
            # ── 创建 Pipeline ──
            pipeline = AgentPipeline(db, conversation_id=req.conversation_id)
            await pipeline.memory.get_or_create_conversation()

            # 发送 pipeline 启动事件（含完整步骤列表）
            yield make_pipeline_start(pipeline.memory.conversation_id)
            await asyncio.sleep(0.02)  # 让前端有时间初始化

            # ════════════════════════════════════════════
            # Step 1: Context Builder (理解问题)
            # ════════════════════════════════════════════
            timer.start("context_builder")
            yield make_step_start("context_builder")
            context_messages = await pipeline.build_context(req.message)
            yield make_step_complete("context_builder", duration_ms=timer.elapsed("context_builder"))

            # ════════════════════════════════════════════
            # Step 2: Memory (读取长期记忆)
            # ════════════════════════════════════════════
            timer.start("memory")
            yield make_step_start("memory")
            # memory 已在 build_context 中加载，此处仅做计时展示
            await asyncio.sleep(0.01)
            yield make_step_complete("memory", duration_ms=timer.elapsed("memory"))

            # ════════════════════════════════════════════
            # Step 3: Context (恢复历史上下文)
            # ════════════════════════════════════════════
            timer.start("context")
            yield make_step_start("context")
            await asyncio.sleep(0.01)
            yield make_step_complete("context",
                duration_ms=timer.elapsed("context"))

            # ════════════════════════════════════════════
            # Step 4: Intent Detector (识别意图)
            # ════════════════════════════════════════════
            timer.start("intent_detector")
            yield make_step_start("intent_detector")
            intent = await pipeline.detect_intent(req.message)
            yield make_intent_event(intent.intent_type, intent.confidence, intent.entities)
            yield make_step_complete("intent_detector",
                duration_ms=timer.elapsed("intent_detector"))

            # ════════════════════════════════════════════
            # Step 5: Planner (制定计划)
            # ════════════════════════════════════════════
            timer.start("planner")
            yield make_step_start("planner")
            plan = await pipeline.plan(req.message, context_messages)
            if plan.steps:
                yield make_plan_event(plan.to_frontend())
            yield make_step_complete("planner",
                duration_ms=timer.elapsed("planner"))

            # ── 聊天模式：直接 LLM 回复 ──
            if not plan.steps:
                timer.start("llm_final")
                yield make_step_start("llm_final")
                full_response = ""
                client, model = await get_ai_client()
                response = await client.chat.completions.create(
                    model=model,
                    messages=context_messages,
                    temperature=0.5,
                    max_tokens=1024,
                    stream=True,
                )
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield make_content(content)

                yield make_step_complete("llm_final",
                    duration_ms=timer.elapsed("llm_final"))

                # 保存
                await pipeline.memory.add_message("user", req.message)
                await pipeline.memory.add_message("assistant", full_response)
                await pipeline.memory.extract_memories_from_message(req.message)
                await pipeline.memory.add_task_memory(req.message, full_response)
                await db.commit()

                # ── 项目关联（Project Workspace 支持） ──
                if req.project_id:
                    try:
                        from ...core.project_manager import ProjectManager
                        pm = ProjectManager(db)
                        await pm.link_conversation(
                            req.project_id,
                            pipeline.memory.conversation_id,
                        )
                        for rec in pipeline._tool_records:
                            await pm.add_tool_record(
                                project_id=req.project_id,
                                tool_name=rec.tool_name,
                                command=rec.command,
                                status=rec.status,
                                duration_ms=int(rec.duration_ms),
                                result_preview=rec.result[:300] if rec.result else "",
                                conversation_id=pipeline.memory.conversation_id,
                            )
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"Project link failed (chat mode): {e}")

                yield make_done(intent=intent.intent_type,
                    conversation_id=pipeline.memory.conversation_id)
                yield "data: [DONE]\n\n"
                return

            # ════════════════════════════════════════════
            # Step 6: Router (路由工具)
            # ════════════════════════════════════════════
            timer.start("router")
            yield make_step_start("router")
            tools = pipeline.route()
            yield make_tools_event(tools)
            yield make_step_complete("router",
                duration_ms=timer.elapsed("router"))

            # ════════════════════════════════════════════
            # Step 7: Executor (调用工具)
            # ════════════════════════════════════════════
            timer.start("executor")
            yield make_step_start("executor")

            for step in plan.steps:
                tool_name = step.tool
                if not tool_name:
                    tool_name = registry.get_tool_for_command(step.action)
                    if not tool_name:
                        continue

                command = step.action
                if step.tool_args and "command" in step.tool_args:
                    command = step.tool_args["command"]

                yield make_tool_start(tool_name, step.step_id, step.description)

                record = await registry.execute(tool_name, command, timeout=30)
                pipeline._tool_records.append(record)

                yield make_tool_result(
                    tool=tool_name,
                    status=record.status,
                    duration_ms=record.duration_ms,
                    result_preview=record.result[:300] if record.result else "",
                    error=record.error[:200] if record.error else "",
                )

                # 失败时尝试备用工具
                if record.status in (ToolStatus.FAILED, ToolStatus.TIMEOUT):
                    fallbacks = [t for t in tools if t != tool_name]
                    if fallbacks:
                        fb = fallbacks[0]
                        yield make_tool_start(fb, step.step_id,
                            f"备用工具: {fb}", is_fallback=True)
                        fb_record = await registry.execute(fb, command, timeout=30)
                        pipeline._tool_records.append(fb_record)
                        yield make_tool_result(
                            tool=fb,
                            status=fb_record.status,
                            duration_ms=fb_record.duration_ms,
                            result_preview=fb_record.result[:300] if fb_record.result else "",
                            error=fb_record.error[:200] if fb_record.error else "",
                            is_fallback=True,
                        )

            yield make_step_complete("executor",
                duration_ms=timer.elapsed("executor"))

            # ════════════════════════════════════════════
            # Step 8: Observation (分析结果)
            # ════════════════════════════════════════════
            timer.start("observation")
            yield make_step_start("observation")
            observation = await pipeline.observe()
            yield make_step_complete("observation",
                duration_ms=timer.elapsed("observation"))

            # ════════════════════════════════════════════
            # Step 9: LLM Final (生成回答)
            # ════════════════════════════════════════════
            timer.start("llm_final")
            yield make_step_start("llm_final")

            # 流式输出 LLM 最终回答
            client, model = await get_ai_client()
            llm_messages = list(context_messages)

            if observation:
                llm_messages.append({
                    "role": "system",
                    "content": f"以下是工具返回的实时数据，请用自然语言回答用户，不要直接输出JSON：\n\n{observation}"
                })
            else:
                llm_messages.append({"role": "user", "content": req.message})

            full_response = ""
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=llm_messages,
                    temperature=0.4,
                    max_tokens=1024,
                    stream=True,
                )
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield make_content(content)
            except Exception as e:
                logger.error(f"LLM stream failed: {e}")
                full_response = observation[:500] or "查询完成"
                yield make_content(full_response)

            yield make_step_complete("llm_final",
                duration_ms=timer.elapsed("llm_final"))

            # ════════════════════════════════════════════
            # Step 10: Save
            # ════════════════════════════════════════════
            await pipeline.save(req.message, full_response)
            await db.commit()

            # ── 项目关联（Project Workspace 支持） ──
            if req.project_id:
                try:
                    from ...core.project_manager import ProjectManager
                    pm = ProjectManager(db)
                    await pm.link_conversation(
                        req.project_id,
                        pipeline.memory.conversation_id,
                    )
                    # 记录工具调用
                    for rec in pipeline._tool_records:
                        await pm.add_tool_record(
                            project_id=req.project_id,
                            tool_name=rec.tool_name,
                            command=rec.command,
                            status=rec.status,
                            duration_ms=int(rec.duration_ms),
                            result_preview=rec.result[:300] if rec.result else "",
                            conversation_id=pipeline.memory.conversation_id,
                        )
                    await db.commit()
                except Exception as e:
                    logger.warning(f"Project link failed: {e}")

            # 完成
            yield make_done(
                intent=intent.intent_type,
                tools_used=[r.tool_name for r in pipeline._tool_records],
                tool_count=len(pipeline._tool_records),
                conversation_id=pipeline.memory.conversation_id,
            )

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield make_error(str(e))

        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )