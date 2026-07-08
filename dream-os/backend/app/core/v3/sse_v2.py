"""SSE v2 — 增强事件协议 (支持多 Agent 维度)

V3 新增事件类型:
  - agent_start: Agent 开始执行
  - agent_tool_call: Agent 调用工具
  - agent_tool_result: 工具返回结果
  - agent_complete: Agent 完成
  - agent_handoff: Agent 间交接
  - loop_iteration: 自主循环迭代
  - progress_update: 进度更新
  - file_created: 文件创建
  - test_result: 测试结果
  - deployment_info: 部署信息
  - confirmation_required: 需要人工确认
"""
import json
from datetime import datetime


class SSEv2:
    """V3 SSE 事件构建器"""

    @staticmethod
    def _format(data: dict) -> str:
        data["timestamp"] = datetime.now().isoformat()
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    # ── 生命周期事件 ──

    @staticmethod
    def dev_start(task_id: str, requirement: str, agents: list[str]) -> str:
        return SSEv2._format({
            "type": "dev_start",
            "task_id": task_id,
            "requirement": requirement[:500],
            "agents": agents,
        })

    @staticmethod
    def dev_complete(task_id: str, success: bool, summary: str, workspace: str) -> str:
        return SSEv2._format({
            "type": "dev_complete",
            "task_id": task_id,
            "success": success,
            "summary": summary[:500],
            "workspace": workspace,
        })

    @staticmethod
    def error(msg: str) -> str:
        return SSEv2._format({
            "type": "error",
            "message": str(msg)[:300],
        })

    @staticmethod
    def done() -> str:
        return "data: [DONE]\n\n"

    # ── Agent 事件 ──

    @staticmethod
    def agent_start(agent: str, name: str, emoji: str, task: str) -> str:
        return SSEv2._format({
            "type": "agent_start",
            "agent": agent,
            "name": name,
            "emoji": emoji,
            "task": task[:200],
        })

    @staticmethod
    def agent_thinking(agent: str, thought: str) -> str:
        return SSEv2._format({
            "type": "agent_thinking",
            "agent": agent,
            "thought": thought[:300],
        })

    @staticmethod
    def agent_tool_call(agent: str, tool: str, arguments: dict, iteration: int) -> str:
        return SSEv2._format({
            "type": "agent_tool_call",
            "agent": agent,
            "tool": tool,
            "arguments": arguments,
            "iteration": iteration,
        })

    @staticmethod
    def agent_tool_result(agent: str, tool: str, success: bool,
                          output: str, iteration: int) -> str:
        return SSEv2._format({
            "type": "agent_tool_result",
            "agent": agent,
            "tool": tool,
            "success": success,
            "output": output[:300],
            "iteration": iteration,
        })

    @staticmethod
    def agent_complete(agent: str, success: bool, output: str,
                       tool_calls: int, duration_ms: float) -> str:
        return SSEv2._format({
            "type": "agent_complete",
            "agent": agent,
            "success": success,
            "output": output[:500],
            "tool_calls": tool_calls,
            "duration_ms": round(duration_ms, 1),
        })

    @staticmethod
    def agent_handoff(from_agent: str, to_agent: str, context: str = "") -> str:
        return SSEv2._format({
            "type": "agent_handoff",
            "from": from_agent,
            "to": to_agent,
            "context": context[:200],
        })

    # ── 自主循环事件 ──

    @staticmethod
    def loop_iteration(iteration: int, max_iterations: int,
                       status: str, reason: str = "") -> str:
        return SSEv2._format({
            "type": "loop_iteration",
            "iteration": iteration,
            "max_iterations": max_iterations,
            "status": status,  # running / retrying / success / failed
            "reason": reason[:200],
        })

    # ── 进度事件 ──

    @staticmethod
    def progress_update(current_agent: str, completed: int, total: int,
                        percent: float, summary: str = "") -> str:
        return SSEv2._format({
            "type": "progress_update",
            "current_agent": current_agent,
            "completed": completed,
            "total": total,
            "percent": round(percent, 1),
            "summary": summary[:200],
        })

    # ── 项目事件 ──

    @staticmethod
    def file_created(filepath: str, action: str = "created", size: int = 0) -> str:
        return SSEv2._format({
            "type": "file_created",
            "filepath": filepath,
            "action": action,
            "size": size,
        })

    @staticmethod
    def test_result(passed: bool, total: int, failures: int, details: str = "") -> str:
        return SSEv2._format({
            "type": "test_result",
            "passed": passed,
            "total": total,
            "failures": failures,
            "details": details[:500],
        })

    @staticmethod
    def deployment_info(url: str, port: int, status: str = "deploying") -> str:
        return SSEv2._format({
            "type": "deployment_info",
            "url": url,
            "port": port,
            "status": status,
        })

    @staticmethod
    def confirmation_required(agent: str, tool: str, command: str, reason: str) -> str:
        return SSEv2._format({
            "type": "confirmation_required",
            "agent": agent,
            "tool": tool,
            "command": command[:200],
            "reason": reason[:200],
        })

    @staticmethod
    def content(text: str) -> str:
        """流式文本输出"""
        return SSEv2._format({"type": "content", "content": text})
