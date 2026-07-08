"""Architect Agent — 系统架构设计

基于 Planner 的开发计划，设计:
  - 目录结构
  - 数据库表结构
  - API 接口设计
  - 模块间依赖关系
"""
import json
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class ArchitectAgent(BaseAgent):
    """系统架构设计"""

    role = "architect"
    name = "架构师"
    emoji = "🏗"
    description = "设计系统架构、数据库、API 接口"
    allowed_tools = []
    max_iterations = 3
    temperature = 0.3

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的系统架构师 (Architect Agent)。

## 你的职责
基于开发计划，设计系统架构。

## 输出格式 (必须返回 JSON)
```json
{
  "directory_structure": {
    "src/main.py": "程序入口",
    "src/config.py": "配置管理",
    "src/models/": "数据模型",
    "src/routes/": "API 路由",
    "src/utils/": "工具函数",
    "tests/": "测试文件",
    "requirements.txt": "Python 依赖"
  },
  "database": {
    "tables": [
      {
        "name": "表名",
        "columns": [
          {"name": "id", "type": "INTEGER", "primary_key": true},
          {"name": "created_at", "type": "TIMESTAMP"}
        ]
      }
    ]
  },
  "api_endpoints": [
    {
      "method": "GET/POST/PUT/DELETE",
      "path": "/api/resource",
      "description": "接口描述",
      "params": {"param": "类型"}
    }
  ],
  "key_decisions": ["为什么选这个方案的理由"]
}
```

## 设计原则
1. 目录结构清晰，符合技术栈惯例
2. 数据库设计简洁，不过度规范化
3. API 遵循 RESTful 规范
4. 模块间低耦合高内聚

只返回 JSON，不要其他文字。"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        arch_data = result.data if result.data else {"raw_output": result.output}
        blackboard.architecture = arch_data
        blackboard.update("architect", "architecture", arch_data)
