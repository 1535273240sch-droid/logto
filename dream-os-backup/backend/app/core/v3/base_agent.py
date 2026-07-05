"""BaseAgent V3 — 自主 Agent 基类

每个 Agent 是一个 LLM + 专属工具集 + ReAct 循环的自治单元。

核心流程:
  1. 接收任务 + 从 Blackboard 读取上下文
  2. 构建专属 system prompt + 可用工具
  3. ReAct 循环: LLM 思考 → 调用工具 → 观察结果 → 再思考...
  4. 直到 LLM 返回最终结论 (无 tool_call)
  5. 将结果写入 Blackboard

安全机制:
  - 工具白名单: Agent 只能使用声明的工具
  - 命令风险分级: SAFE / DANGEROUS (需确认) / FORBIDDEN
  - 迭代上限: 防止无限循环
"""
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from ..ai_provider import get_ai_client
from ..risk_classifier import classify, RiskLevel
from ...tools.base import ToolManager, BaseTool
from .blackboard import SharedBlackboard

logger = logging.getLogger("dream-os.v3.agent")

# 事件回调类型: async (event_dict) -> None
EventCallback = Callable[[dict], Awaitable[None]]


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str = ""           # LLM 最终输出
    data: dict = field(default_factory=dict)  # 结构化数据 (写入 blackboard 的内容)
    tool_calls: int = 0        # 工具调用次数
    duration_ms: float = 0
    error: str = ""


class BaseAgent(ABC):
    """V3 Agent 基类 — 内置 ReAct 循环 + function calling"""

    # ── Agent 身份 ──
    role: str = "base"           # planner/architect/coder/executor/reviewer/tester/deployer/reporter
    name: str = "基础 Agent"     # 显示名称
    emoji: str = "🤖"
    description: str = ""

    # ── 工具配置 ──
    allowed_tools: list[str] = []  # 工具白名单 (tool names)
    max_iterations: int = 8      # ReAct 循环最大迭代

    # ── LLM 配置 ──
    temperature: float = 0.3
    max_tokens: int = 2048

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent 专属系统提示词"""
        ...

    def __init__(self):
        self.tool_manager: ToolManager | None = None
        self._tool_schemas: list[dict] = []

    def setup_tools(self, tool_manager: ToolManager):
        """注册 Agent 可用的工具 (从全局 ToolManager 中筛选)"""
        self.tool_manager = ToolManager()  # 独立实例，只包含白名单工具
        for name in self.allowed_tools:
            tool = tool_manager.get(name)
            if tool:
                self.tool_manager.register(tool)
        self._tool_schemas = self.tool_manager.list_schemas()

    async def run(
        self,
        task: str,
        blackboard: SharedBlackboard,
        emit: EventCallback,
        workspace_path: str = "",
    ) -> AgentResult:
        """执行任务 — ReAct 循环

        Args:
            task: 当前 Agent 需要完成的具体任务描述
            blackboard: 共享上下文
            emit: SSE 事件回调
            workspace_path: 工作空间路径

        Returns:
            AgentResult
        """
        start_time = time.time()
        total_tool_calls = 0

        # 发送 agent_start 事件
        await emit({
            "type": "agent_start",
            "agent": self.role,
            "name": self.name,
            "emoji": self.emoji,
            "task": task[:200],
        })

        try:
            # 获取 LLM 客户端
            client, model = await get_ai_client()

            # 构建上下文
            context = blackboard.get_context_for(self.role)
            workspace_info = f"工作空间路径: {workspace_path}" if workspace_path else ""

            # 构建消息
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]
            if workspace_info:
                messages.append({"role": "system", "content": workspace_info})
            if context:
                messages.append({"role": "system", "content": f"项目上下文:\n{context}"})
            messages.append({"role": "user", "content": task})

            # ── ReAct 循环 ──
            for iteration in range(1, self.max_iterations + 1):
                # 调用 LLM
                kwargs = dict(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                if self._tool_schemas:
                    kwargs["tools"] = self._tool_schemas
                    kwargs["tool_choice"] = "auto"

                response = await client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

                # 无 tool_call → 最终结论
                if not msg.tool_calls:
                    output = msg.content or ""
                    result = AgentResult(
                        success=True,
                        output=output,
                        data=self._parse_output(output),
                        tool_calls=total_tool_calls,
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                    # 写入 blackboard
                    self._write_to_blackboard(blackboard, result)
                    # 发送完成事件
                    await emit({
                        "type": "agent_complete",
                        "agent": self.role,
                        "success": True,
                        "output": output[:500],
                        "tool_calls": total_tool_calls,
                        "duration_ms": result.duration_ms,
                    })
                    return result

                # 有 tool_call → 执行工具
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    total_tool_calls += 1

                    # 发送 tool_call 事件
                    await emit({
                        "type": "agent_tool_call",
                        "agent": self.role,
                        "tool": tool_name,
                        "arguments": arguments,
                        "iteration": iteration,
                    })

                    # 执行工具
                    tool_result = await self._execute_tool(
                        tool_name, arguments, workspace_path, emit
                    )

                    # 记录到 blackboard
                    blackboard.execution_log.append({
                        "agent": self.role,
                        "tool": tool_name,
                        "command": arguments.get("command", str(arguments))[:200],
                        "success": tool_result["success"],
                        "output": tool_result["output"][:500],
                        "iteration": iteration,
                    })

                    # 发送 tool_result 事件
                    await emit({
                        "type": "agent_tool_result",
                        "agent": self.role,
                        "tool": tool_name,
                        "success": tool_result["success"],
                        "output": tool_result["output"][:300],
                        "iteration": iteration,
                    })

                    # 将工具结果加入消息历史
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result["output"][:4000],
                    })

            # 迭代上限
            result = AgentResult(
                success=False,
                output=f"Agent {self.name} 达到最大迭代次数 ({self.max_iterations})",
                tool_calls=total_tool_calls,
                duration_ms=(time.time() - start_time) * 1000,
                error="max_iterations_exceeded",
            )
            await emit({
                "type": "agent_complete",
                "agent": self.role,
                "success": False,
                "output": result.output,
                "tool_calls": total_tool_calls,
                "duration_ms": result.duration_ms,
            })
            return result

        except Exception as e:
            logger.error(f"Agent {self.role} failed: {e}", exc_info=True)
            result = AgentResult(
                success=False,
                output="",
                tool_calls=total_tool_calls,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
            await emit({
                "type": "agent_complete",
                "agent": self.role,
                "success": False,
                "output": f"Agent 执行失败: {e}",
                "error": str(e)[:200],
                "tool_calls": total_tool_calls,
                "duration_ms": result.duration_ms,
            })
            return result

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        workspace_path: str,
        emit: EventCallback,
    ) -> dict:
        """执行单个工具调用 (带安全检查)"""
        if not self.tool_manager:
            return {"success": False, "output": "ToolManager 未初始化"}

        tool = self.tool_manager.get(tool_name)
        if not tool:
            return {"success": False, "output": f"工具 '{tool_name}' 不可用 (不在 {self.role} 的工具白名单中)"}

        command = arguments.get("command", "")

        # 风险分级 (仅对 shell_exec)
        if tool_name in ("shell_exec", "shell_safe"):
            risk, reason = classify(command) if command else (RiskLevel.SAFE, "")

            if risk == RiskLevel.FORBIDDEN:
                return {"success": False, "output": f"🚫 安全拦截: {reason}"}

            if risk == RiskLevel.DANGEROUS:
                # 在自主模式下，危险命令需要人工确认
                await emit({
                    "type": "confirmation_required",
                    "agent": self.role,
                    "tool": tool_name,
                    "command": command,
                    "reason": reason,
                })
                # 自主模式下默认拒绝危险命令 (安全边界)
                return {
                    "success": False,
                    "output": f"⏸️ 危险操作已拦截 (需人工确认): {reason}。请通过手动方式执行此命令。",
                }

        # 设置工作目录 (如果工具支持)
        try:
            if hasattr(tool, "work_dir") and workspace_path:
                tool.work_dir = workspace_path
            if hasattr(tool, "base_dir") and workspace_path:
                tool.base_dir = workspace_path
        except Exception:
            pass

        # 执行
        try:
            timeout = arguments.get("timeout", 60)
            result = await tool.execute(command, timeout=timeout)
            output = result.stdout if result.success else f"错误: {result.stderr or result.stdout}"
            return {
                "success": result.success,
                "output": output[:4000],
                "exit_code": result.exit_code,
            }
        except Exception as e:
            return {"success": False, "output": f"工具执行异常: {e}"}

    def _parse_output(self, output: str) -> dict:
        """解析 LLM 输出为结构化数据 (子类可覆盖)"""
        # 尝试提取 JSON
        try:
            # 查找 JSON 块
            if "```json" in output:
                start = output.index("```json") + 7
                end = output.index("```", start)
                return json.loads(output[start:end].strip())
            if output.strip().startswith("{"):
                return json.loads(output.strip())
        except (json.JSONDecodeError, ValueError):
            pass
        return {"raw_output": output[:1000]}

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        """将 Agent 结果写入 blackboard (子类可覆盖)"""
        blackboard.update(self.role, "history", {
            "agent": self.role,
            "success": result.success,
            "output": result.output[:500],
            "tool_calls": result.tool_calls,
            "duration_ms": result.duration_ms,
        })

    def to_info(self) -> dict:
        return {
            "role": self.role,
            "name": self.name,
            "emoji": self.emoji,
            "description": self.description,
            "tools": self.allowed_tools,
        }
