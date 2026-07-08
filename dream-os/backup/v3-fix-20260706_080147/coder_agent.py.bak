"""Coder Agent — 代码编写 + 文件创建

基于架构设计，创建项目文件并编写代码。
使用 file_read 工具 (支持 read/write/mkdir 操作) 写入文件。

工具:
  - file_read: 读写文件 (命令前缀 read:/write:/mkdir:)
  - shell_exec: 执行命令 (查看目录结构等)
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class CoderAgent(BaseAgent):
    """代码编写 + 文件创建"""

    role = "coder"
    name = "程序员"
    emoji = "💻"
    description = "创建文件、编写代码、实现功能"
    allowed_tools = ["file_read", "shell_exec"]
    max_iterations = 15
    temperature = 0.2
    max_tokens = 4096

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的程序员 (Coder Agent)。

## 你的职责
根据架构设计，创建项目文件并编写完整的代码。

## 工作流程
1. 查看架构设计中的目录结构
2. 使用 file_read 工具 (write 命令) 逐个创建文件
3. 每个文件写入完整、可运行的代码
4. 代码要包含必要的注释
5. 确保文件之间的引用关系正确

## file_read 工具用法
file_read 工具支持 4 种操作 (通过命令前缀区分):

1. 写文件 (最重要):
   命令格式: write:相对路径:文件内容
   例如: write:src/main.py:print("hello")
   注意：路径相对于工作空间根目录。源码文件应放在 src/ 下，测试放在 tests/ 下

2. 读文件:
   命令格式: read:相对路径
   例如: read:src/main.py

3. 创建目录:
   命令格式: mkdir:目录路径

4. 列目录:
   命令格式: list:目录路径

## shell_exec 工具用法
用于查看目录结构、检查文件是否已存在
命令格式: ls -la src/

## 代码质量要求
1. 代码完整可运行，不能有省略号或 TODO
2. 包含必要的错误处理
3. 函数和类要有清晰的职责
4. 遵守语言惯例和最佳实践
5. 配置文件要包含实际可用的默认值
6. 一次只调用一个工具，等待结果后再调用下一个

## 完成条件
当所有文件都创建完成后，输出一个 JSON 摘要 (不要再调用工具):
```json
{
  "files_created": ["main.py", "config.py"],
  "total_lines": 500,
  "entry_point": "main.py",
  "run_command": "python main.py"
}
```"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        """收集创建的文件信息"""
        files_info = {}

        # 从执行日志中提取文件写入记录
        for log in blackboard.execution_log:
            if log.get("agent") == "coder" and log.get("tool") == "file_read":
                cmd = log.get("command", "")
                if cmd.startswith("write:"):
                    parts = cmd.split(":", 2)
                    if len(parts) >= 3:
                        filepath = parts[1]
                        content = parts[2]
                        files_info[filepath] = {
                            "action": "created",
                            "content_preview": content[:200],
                            "lines": content.count("\n") + 1,
                            "size": len(content),
                        }

        # 也从 LLM 输出中解析
        if result.data and "files_created" in result.data:
            for fn in result.data["files_created"]:
                if fn not in files_info:
                    files_info[fn] = {"action": "created", "content_preview": ""}

        blackboard.files.update(files_info)
        blackboard.update("coder", "files", files_info)
