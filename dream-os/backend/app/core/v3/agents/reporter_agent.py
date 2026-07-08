"""Reporter Agent — 文档生成 + 成果交付

生成:
  - README.md
  - API 文档
  - 部署文档
  - 开发报告
  - 变更日志
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class ReporterAgent(BaseAgent):
    """文档生成 + 成果交付"""

    role = "reporter"
    name = "报告员"
    emoji = "📝"
    description = "生成 README、API 文档、开发报告"
    allowed_tools = ["file_read", "shell_exec"]
    max_iterations = 8
    temperature = 0.4
    max_tokens = 4096

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的报告员 (Reporter Agent)。

## 你的职责
为项目生成完整的文档和开发报告。

## 需要生成的文档
1. **README.md** — 项目说明、快速开始、API 文档
2. **开发报告** — 开发过程总结、文件清单、测试结果

## 工作流程
1. 读取项目文件，了解项目结构
2. 使用 file_read 工具 (write 命令) 写入 README.md 到 docs/README.md
3. 生成开发报告

## README.md 格式
```markdown
# 项目名称

## 简介
项目描述

## 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python src/main.py
```

## API 文档
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/health | 健康检查 |

## 项目结构
```
src/
├── main.py
├── config.py
└── ...
```

## 开发报告格式 (JSON)
```json
{
  "project_name": "项目名",
  "summary": "开发总结",
  "files_created": ["文件列表"],
  "total_files": 10,
  "total_lines": 500,
  "tech_stack": "Python + FastAPI",
  "test_status": "passed/failed",
  "deployment_url": "http://localhost:8000",
  "known_issues": ["已知问题"],
  "next_steps": ["后续建议"]
}
```

## 重要
- 文档要准确反映实际代码
- README 要让新手能快速上手
- 开发报告要客观总结"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        report_data = result.data if result.data else {"raw_output": result.output}
        blackboard.reports.append({
            "agent": "reporter",
            "type": "dev_report",
            "data": report_data,
        })
        blackboard.update("reporter", "reports", report_data)
