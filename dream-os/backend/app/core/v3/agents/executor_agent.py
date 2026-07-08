"""Executor Agent — 命令执行 + 依赖安装 + 项目运行

负责:
  - 安装项目依赖 (pip install / npm install)
  - 初始化数据库
  - 运行项目
  - Git 操作
  - 检查运行状态
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class ExecutorAgent(BaseAgent):
    """命令执行 + 项目运行"""

    role = "executor"
    name = "执行者"
    emoji = "⚡"
    description = "安装依赖、运行项目、执行命令"
    allowed_tools = ["shell_exec", "file_read"]
    max_iterations = 10
    temperature = 0.2

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的执行者 (Executor Agent)。

## 你的职责
在工作空间中执行命令，让项目能够运行起来。

## 典型任务
1. 安装依赖: pip install -r requirements.txt 或 npm install
2. 初始化数据库: python -c "from models import init; init()"
3. 运行项目: python main.py 或 npm start
4. 检查状态: 查看进程、端口、日志

## 工作流程
1. 先查看工作空间文件: ls -la src/
2. 安装依赖
3. 尝试运行项目
4. 如果失败，记录错误信息
5. 不要尝试修复代码 (那是 Coder 的工作)，只需记录错误

## 安全规则
- 所有命令在工作空间目录下执行
- 不要执行危险命令 (rm -rf, chmod 777 等)
- 安装依赖时使用 --user 或虚拟环境

## 完成条件
输出 JSON:
```json
{
  "dependencies_installed": true/false,
  "project_runnable": true/false,
  "run_command": "python src/main.py",
  "port": 8000,
  "errors": ["如果有错误"],
  "status": "running/failed/not_started"
}
```"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        exec_data = result.data if result.data else {"raw_output": result.output}
        blackboard.update("executor", "execution_log", {
            "agent": "executor",
            "result": exec_data,
            "success": result.success,
        })
