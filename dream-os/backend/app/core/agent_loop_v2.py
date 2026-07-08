"""ReAct Agent Loop V2 — 带Planner的智能循环（低资源优化版）"""
import json
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..models.task import Task
from ..tools import ToolManager, ShellTool, FileTool, HttpTool
from ..logger import TaskLogger
from ..core.memory import ContextMemoryManager
from .risk_classifier import classify, RiskLevel
from .planner import Planner, ExecutionPlan

# 全局确认挂起存储
_pending_confirmations: dict[str, asyncio.Event] = {}
_confirmation_results: dict[str, bool] = {}


def signal_confirmation(task_id: str, confirmed: bool):
    _confirmation_results[task_id] = confirmed
    if task_id in _pending_confirmations:
        _pending_confirmations[task_id].set()


async def request_confirmation(task_id: str, cmd: str, reason: str, ws_send, timeout: int = 60) -> bool:
    event = asyncio.Event()
    _pending_confirmations[task_id] = event
    try:
        await ws_send(json.dumps({
            "type": "confirm_required",
            "task_id": task_id,
            "command": cmd,
            "reason": reason,
            "timeout": timeout,
        }, ensure_ascii=False))
    except Exception:
        pass
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return _confirmation_results.get(task_id, False)
    except asyncio.TimeoutError:
        return False
    finally:
        _pending_confirmations.pop(task_id, None)
        _confirmation_results.pop(task_id, None)


AGENT_SYSTEM_PROMPT = """你是「何惜 AI」，一个能自主规划和执行任务的智能助手。

## 判断原则（重要）
1. 用户问的是**常识性问题**（历史人物、诗词、百科知识、简单解释）→ **直接回答，不调用工具**
2. 用户问的是**实时信息**（天气、新闻、服务器状态、当前数据）→ **调用工具查询**
3. 用户要求**操作服务器/文件/生成图片** → **调用工具执行**
4. 不确定时，优先直接回答，不要无事搜索

## 可用工具
- shell_exec: Linux命令（文件操作、系统查询、数据处理）
- http_fetch: 联网请求（搜索、API、网页抓取，仅限实时信息）
- file_read: 读取文件
- file_write: 写入文件
- file_list: 列出目录

## 工作流程
1. 收到任务 → 判断是否需要工具
2. 不需要 → 直接给出简洁准确的回答
3. 需要工具 → 调用一次工具 → 分析结果
4. 工具失败 → 最多重试1次，仍失败就告知用户原因，不要机械重复
5. 成功 → 整理结果回复用户

## 规则
- 每次只调用一个工具
- **常识问题严禁使用 http_fetch 搜索**
- 简单对话（问候、谢谢、你是谁）直接回复，不调用工具
- 最终回复要简洁、自然，不要暴露工具调用细节（如"我调用了xxx"）
- 工具查询失败时，直接说明原因并给出基于自身知识的最佳回答
- 如果任务包含已提供的执行计划，按计划执行"""


class AgentLoopV2:
    """ReAct 循环 V2：Plan → Execute → Review → Report（低资源优化版）"""

    def __init__(self):
        settings = get_settings()
        self.max_iterations = int(os.getenv("MAX_LOOP_ITERATIONS", "10"))
        self.tool_manager = ToolManager()
        self.planner = Planner()
        self._init_tools()

    def _init_tools(self):
        self.tool_manager.register(ShellTool())
        self.tool_manager.register(FileTool())
        self.tool_manager.register(HttpTool())
        self._tool_schemas = self.tool_manager.list_schemas()

    async def run(
        self,
        task: Task,
        db: AsyncSession,
        ws_send=None,
    ) -> str:
        logger = TaskLogger(task.id, db)

        # V1.5: 使用 ContextMemoryManager
        memory_manager = ContextMemoryManager(db)
        await memory_manager.get_or_create_conversation()
        await memory_manager.add_message("user", task.user_input)

        # ── Phase 1: 规划 ──
        from .ai_provider import get_ai_client
        client, model = await get_ai_client()

        plan: ExecutionPlan = await self.planner.plan(task.user_input, client, model)
        await self._push(ws_send, json.dumps(plan.to_frontend(), ensure_ascii=False))

        task.status = "running"
        task.plan = plan.to_frontend()
        await db.flush()

        # 无需工具则直接回复
        if not plan.steps:
            context_messages = await memory_manager.build_context_prompt(AGENT_SYSTEM_PROMPT)
            context_messages.append({"role": "user", "content": task.user_input})

            response = await client.chat.completions.create(
                model=model,
                messages=context_messages,
                temperature=0.5,
                max_tokens=int(os.getenv("AI_MAX_TOKENS", "1024")),
            )
            answer = response.choices[0].message.content or ""
            task.result = answer
            task.status = "completed"

            # V1.5: 保存回复
            await memory_manager.add_message("assistant", answer)
            await memory_manager.add_task_memory(task.user_input, answer)
            await db.flush()

            await self._push(ws_send, json.dumps({
                "type": "final", "answer": answer, "iterations": 0,
            }, ensure_ascii=False))
            return answer

        # ── Phase 2: 执行 ReAct 循环 ──
        context_messages = await memory_manager.build_context_prompt(AGENT_SYSTEM_PROMPT)
        context_messages.append({"role": "user", "content": task.user_input})
        context_messages.append({
            "role": "system",
            "content": f"执行计划:\n{json.dumps(plan.to_frontend(), ensure_ascii=False)}",
        })
        messages = context_messages

        iteration = 0
        tool_results = []
        failed_steps = {}

        final_answer = ""
        while iteration < self.max_iterations:
            iteration += 1

            all_done = all(s.status in ("done", "failed") for s in plan.steps)
            if all_done and iteration > len(plan.steps):
                break

            next_step = None
            for s in plan.steps:
                if s.status == "pending":
                    deps_done = all(
                        plan.steps[d - 1].status == "done"
                        for d in s.depends_on if 1 <= d <= len(plan.steps)
                    )
                    if deps_done:
                        next_step = s
                        break

            response = await self._call_model(messages, client, model)

            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    step = next_step
                    if step:
                        step.status = "running"
                        await self._push(ws_send, json.dumps({
                            "type": "step_update",
                            "step_id": step.step_id,
                            "status": "running",
                            "description": step.description,
                        }, ensure_ascii=False))

                    await self._push(ws_send, json.dumps({
                        "type": "step", "iteration": iteration,
                        "tool": tool_name, "arguments": arguments,
                    }, ensure_ascii=False))

                    tool = self.tool_manager.get(tool_name)
                    if not tool:
                        result = f"未知工具: {tool_name}"
                        success = False
                    else:
                        try:
                            cmd = arguments.get("command", "")
                            if tool_name == "http_fetch":
                                risk, reason = RiskLevel.SAFE, "http_fetch 只读"
                            else:
                                risk, reason = classify(cmd) if cmd else (RiskLevel.SAFE, "")

                            if risk == RiskLevel.FORBIDDEN:
                                result = f"🚫 安全拦截: {reason}"
                                success = False
                            elif risk == RiskLevel.DANGEROUS:
                                task.status = "awaiting_confirmation"
                                confirmed = await request_confirmation(task.id, cmd, reason, ws_send)
                                task.status = "running"
                                if confirmed:
                                    r = await tool.execute(cmd, timeout=30)
                                    result = r.stdout if r.success else f"错误: {r.stderr}"
                                    success = r.success
                                else:
                                    result = f"⏸️ 操作未获授权: {reason}"
                                    success = False
                            else:
                                r = await tool.execute(cmd, timeout=30)
                                result = r.stdout if r.success else f"错误: {r.stderr}"
                                success = r.success
                        except Exception as e:
                            result = f"工具异常: {str(e)}"
                            success = False

                    if step:
                        step_key = step.step_id
                        if not success:
                            failed_steps[step_key] = failed_steps.get(step_key, 0) + 1
                            if failed_steps[step_key] >= 3:
                                step.status = "failed"
                        else:
                            step.status = "done"
                            failed_steps.pop(step_key, None)

                        await self._push(ws_send, json.dumps({
                            "type": "step_update",
                            "step_id": step.step_id,
                            "status": step.status,
                            "result_preview": str(result)[:200],
                        }, ensure_ascii=False))

                    await logger.log(
                        step_id=iteration,
                        step_name=f"ReAct-{tool_name}",
                        agent="react-v2",
                        tool=tool_name,
                        command=arguments.get("command", str(arguments)),
                        duration_ms=0,
                        exit_code=0 if success else 1,
                        stdout=str(result)[:5000],
                        stderr="",
                        success=success,
                    )

                    tool_results.append({
                        "step": step.step_id if step else None,
                        "tool": tool_name,
                        "success": success,
                        "result": str(result)[:1000],
                    })

                    await self._push(ws_send, json.dumps({
                        "type": "step_result", "iteration": iteration,
                        "tool": tool_name, "result": str(result)[:2000],
                    }, ensure_ascii=False))

                    messages.append({
                        "role": "assistant", "content": None,
                        "tool_calls": [{
                            "id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }]
                    })
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": str(result)[:5000],
                    })
            else:
                final_answer = response.content or "任务已完成"
                break

        # ── Phase 3: 最终报告 ──
        if not final_answer:
            final_answer = await self._generate_final_report(
                messages, tool_results, plan, client, model
            )

        task.result = final_answer
        task.status = "completed"

        # V1.5: 保存回复
        await memory_manager.add_message("assistant", final_answer)
        await memory_manager.add_task_memory(task.user_input, final_answer)

        # 后台维护（fire-and-forget）
        try:
            async def _summarize(text):
                c, m = await get_ai_client()
                r = await c.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": "你是高效对话摘要助手。"},
                        {"role": "user", "content": f"总结:\n\n{text[:4000]}"},
                    ],
                    temperature=0.3, max_tokens=300,
                )
                return r.choices[0].message.content or ""
            await memory_manager.schedule_async_maintenance(_summarize)
        except Exception:
            pass

        await db.flush()

        await self._push(ws_send, json.dumps({
            "type": "final",
            "answer": final_answer,
            "iterations": iteration,
            "steps_completed": sum(1 for s in plan.steps if s.status == "done"),
            "steps_total": len(plan.steps),
            "tool_results": tool_results,
        }, ensure_ascii=False))

        return final_answer

    async def _generate_final_report(self, messages, tool_results, plan, client, model) -> str:
        summary_prompt = f"""根据执行结果，给用户一个简洁、自然的最终回复。

任务: {plan.task_summary}
步骤结果:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

要求:
- 像正常对话一样回复，不要出现"工具使用"、"执行结果"等技术术语
- 不要暴露工具调用过程
- 简洁，不超过300字"""
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是何惜AI，汇报任务结果。"},
                    {"role": "user", "content": summary_prompt},
                ],
                temperature=0.5,
                max_tokens=1024,
            )
            return response.choices[0].message.content or "任务完成"
        except Exception:
            return f"任务完成，共执行 {len(tool_results)} 个步骤"

    async def _call_model(self, messages: list[dict], client, model: str):
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
        )
        if self._tool_schemas:
            kwargs["tools"] = self._tool_schemas
            kwargs["tool_choice"] = "auto"
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message

    async def _push(self, ws_send, data: str):
        if ws_send:
            try:
                await ws_send(data)
            except Exception:
                pass