"""ReAct Agent Loop — 模型自主决策每一步操作，替代固定步骤脚本
V1.5 优化版：使用三层 ContextMemoryManager，异步后台维护
"""
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


# 全局确认挂起存储 — 等待用户对 DANGEROUS 命令的确认/拒绝
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
        result = _confirmation_results.get(task_id, False)
    except asyncio.TimeoutError:
        result = False
    finally:
        _pending_confirmations.pop(task_id, None)
        _confirmation_results.pop(task_id, None)
    return result


SYSTEM_PROMPT = """你叫何惜，服务器助手。直接执行命令，别废话。

可用工具:
- shell_exec: 执行Linux命令（文件、进程、服务管理）
- http_fetch: 联网HTTP请求
- file_read/write/list: 文件读写

规则:
1. 每次只调一个工具
2. 做完直接总结结果
3. 问候直接回，不调工具
4. 错误最多重试2次"""


class AgentLoop:
    """ReAct 循环: Observation → Reasoning → Action → Observation → ..."""

    def __init__(self):
        settings = get_settings()
        self.max_iterations = int(os.getenv("MAX_LOOP_ITERATIONS", "5"))
        self.tool_manager = ToolManager()
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
        """执行 ReAct 循环直到任务完成或达到最大步数"""
        logger = TaskLogger(task.id, db)

        # V1.5: 使用 ContextMemoryManager 构建 prompt
        memory_manager = ContextMemoryManager(db)
        await memory_manager.get_or_create_conversation()
        await memory_manager.add_message("user", task.user_input)
        context_messages = await memory_manager.build_context_prompt(SYSTEM_PROMPT)
        messages = context_messages

        task.status = "running"
        await db.flush()

        iteration = 0
        final_answer = ""

        while iteration < self.max_iterations:
            iteration += 1

            # 调用模型（带 tools）
            response = await self._call_model(messages)

            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    await self._push(ws_send, json.dumps({
                        "type": "step",
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": arguments,
                    }, ensure_ascii=False))

                    tool = self.tool_manager.get(tool_name)
                    if not tool:
                        result = f"未知工具: {tool_name}"
                    else:
                        try:
                            cmd = arguments.get("command", "")
                            if tool_name == "http_fetch":
                                risk, reason = RiskLevel.SAFE, "http_fetch 只读操作"
                            else:
                                risk, reason = classify(cmd) if cmd else (RiskLevel.SAFE, "")

                            if risk == RiskLevel.FORBIDDEN:
                                result = f"🚫 安全拦截: {reason}"

                            elif risk == RiskLevel.DANGEROUS:
                                task.status = "awaiting_confirmation"
                                task.plan = {"confirm_cmd": cmd, "confirm_reason": reason}
                                await db.flush()
                                confirmed = await request_confirmation(
                                    task.id, cmd, reason, ws_send
                                )
                                task.status = "running"
                                task.plan = None
                                await db.flush()

                                if confirmed:
                                    r = await tool.execute(cmd, timeout=30)
                                    result = r.stdout if r.success else f"错误: {r.stderr}"
                                else:
                                    result = f"⏸️ 操作需确认但未获授权或已超时: {reason}"

                            else:
                                r = await tool.execute(cmd, timeout=30)
                                result = r.stdout if r.success else f"错误: {r.stderr}"
                        except Exception as e:
                            result = f"工具执行异常: {str(e)}"

                    # 记录日志
                    await logger.log(
                        step_id=iteration,
                        step_name=f"ReAct-{tool_name}",
                        agent="react",
                        tool=tool_name,
                        command=arguments.get("command", str(arguments)),
                        duration_ms=0,
                        exit_code=0,
                        stdout=str(result)[:5000],
                        stderr="",
                        success=True,
                    )

                    await self._push(ws_send, json.dumps({
                        "type": "step_result",
                        "iteration": iteration,
                        "tool": tool_name,
                        "result": str(result)[:2000],
                    }, ensure_ascii=False))

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)[:5000],
                    })
            else:
                # 无 tool_calls → 完成任务
                final_answer = response.content or ""
                task.result = final_answer
                task.status = "completed"

                # V1.5: 保存回复 + 后台维护
                await memory_manager.add_message("assistant", final_answer)

                # 兼容旧版任务记忆
                await memory_manager.add_task_memory(task.user_input, final_answer)

                # 提交后台维护（异步调度，不阻塞）
                from .ai_provider import get_ai_client
                async def _summarize(text):
                    client, model = await get_ai_client()
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "你是高效对话摘要助手，总结这段对话。"},
                            {"role": "user", "content": f"请总结:\n\n{text[:4000]}"},
                        ],
                        temperature=0.3,
                        max_tokens=300,
                    )
                    return response.choices[0].message.content or ""

                await memory_manager.schedule_async_maintenance(_summarize)

                await db.flush()

                await self._push(ws_send, json.dumps({
                    "type": "final",
                    "answer": final_answer,
                    "iterations": iteration,
                }, ensure_ascii=False))
                return final_answer

        # 达到最大迭代
        final_answer = f"任务未完成，已执行 {self.max_iterations} 步（达到上限）"
        task.result = final_answer
        task.status = "failed"
        task.error_message = "达到最大迭代次数"

        await memory_manager.add_message("user", task.user_input)
        await memory_manager.add_message("assistant", final_answer)
        await memory_manager.add_task_memory(task.user_input, final_answer)
        await db.flush()

        await self._push(ws_send, json.dumps({
            "type": "final",
            "answer": final_answer,
            "iterations": iteration,
            "maxed_out": True,
        }, ensure_ascii=False))
        return final_answer

    async def _call_model(self, messages: list[dict]):
        from .ai_provider import get_ai_client
        client, model = await get_ai_client()

        kwargs = dict(
            model=model,
            messages=messages,
            temperature=float(os.getenv("AI_TEMPERATURE", "0.5")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "1024")),
        )

        tool_schemas = self._tool_schemas
        if tool_schemas:
            kwargs["tools"] = tool_schemas
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message

    async def _push(self, ws_send, data: str):
        if ws_send:
            try:
                await ws_send(data)
            except Exception:
                pass