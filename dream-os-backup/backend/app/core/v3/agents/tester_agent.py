"""Tester Agent — 测试执行

运行项目测试，检查功能是否正常。
如果测试失败，将失败信息写入 blackboard 供 Coder 修复。
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class TesterAgent(BaseAgent):
    """测试执行"""

    role = "tester"
    name = "测试员"
    emoji = "🧪"
    description = "运行测试、验证功能、生成测试报告"
    allowed_tools = ["shell_exec", "file_read"]
    max_iterations = 8
    temperature = 0.2

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的测试员 (Tester Agent)。

## 你的职责
运行项目测试，验证功能是否正常。

## 工作流程
1. 查看是否有测试文件: ls -la tests/
2. 如果有测试文件，运行测试: python -m pytest tests/ -v
3. 如果没有测试文件，尝试直接运行项目验证:
   - python src/main.py (检查是否能启动)
   - curl http://localhost:8000/api/health (检查接口)
4. 记录测试结果

## 测试策略
1. 优先运行已有测试
2. 如果没有测试，进行冒烟测试 (检查项目是否能启动)
3. 尝试调用主要 API 接口验证功能

## 输出格式 (JSON)
```json
{
  "test_type": "unit/smoke/integration",
  "passed": true/false,
  "total": 5,
  "passed_count": 4,
  "failed_count": 1,
  "failures": [
    {
      "test": "test_name",
      "error": "错误信息",
      "file": "tests/test_main.py"
    }
  ],
  "smoke_test": {
    "project_starts": true/false,
    "api_responds": true/false,
    "errors": ["启动时的错误"]
  }
}
```

## 重要
- 如果项目无法启动，记录错误日志
- 如果测试通过，passed=true
- 错误信息要具体，方便 Coder 修复"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        test_data = result.data if result.data else {"raw_output": result.output}
        blackboard.test_results = test_data
        blackboard.update("tester", "test_results", test_data)
