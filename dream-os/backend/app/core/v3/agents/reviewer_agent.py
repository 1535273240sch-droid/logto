"""Reviewer Agent — 代码审查

检查代码质量、安全漏洞、逻辑错误、性能问题。
发现问题后写入 blackboard，Coder 会在下一轮迭代中修复。
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class ReviewerAgent(BaseAgent):
    """代码审查"""

    role = "reviewer"
    name = "审查员"
    emoji = "🔍"
    description = "检查代码质量、安全漏洞、逻辑错误"
    allowed_tools = ["file_read", "shell_exec"]
    max_iterations = 8
    temperature = 0.3

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的代码审查员 (Reviewer Agent)。

## 你的职责
审查项目代码，发现问题并记录。

## 审查项
1. **语法检查**: 代码是否有语法错误
2. **导入检查**: import 语句是否正确
3. **逻辑检查**: 是否有明显的逻辑错误
4. **安全检查**: 是否有 SQL 注入、XSS 等安全漏洞
5. **性能检查**: 是否有明显的性能问题
6. **规范检查**: 命名、缩进、注释是否规范

## 工作流程
1. 查看工作空间文件列表: ls -la src/
2. 逐个读取关键文件: file_read read:main.py
3. 分析代码
4. 记录所有发现的问题

## 输出格式 (JSON)
```json
{
  "issues_found": true/false,
  "issues": [
    {
      "file": "main.py",
      "line": 10,
      "severity": "error/warning/info",
      "category": "syntax/logic/security/performance/style",
      "message": "问题描述",
      "suggestion": "修复建议"
    }
  ],
  "overall_quality": "good/acceptable/poor",
  "can_proceed": true/false
}
```

## 重要
- 只记录真实的问题，不要吹毛求疵
- error 级别的问题必须修复才能继续
- warning 级别的问题建议修复
- 如果代码质量合格，issues 为空数组"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        review_data = result.data if result.data else {"raw_output": result.output}
        issues = review_data.get("issues", [])
        blackboard.review_issues = issues
        blackboard.update("reviewer", "review_issues", issues)
