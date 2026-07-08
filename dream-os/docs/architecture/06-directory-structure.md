# 06 - 目录结构

```
dream-os/
├── core/                          # 系统核心 (只读)
│   ├── __init__.py
│   ├── event_bus.py               # 事件总线
│   ├── quality_guardian/          # 质量门禁
│   │   ├── __init__.py
│   │   ├── guardian.py            # 主审核模块
│   │   ├── rule_engine.py         # 12 条规则
│   │   ├── regression.py          # 17 模块回归测试
│   │   └── report.py              # 质量报告
│   └── project_brain/             # 项目状态内核
│       ├── __init__.py
│       ├── brain.py               # 主模块
│       └── state.py               # 状态数据模型
├── services/                      # 服务层 (只读)
│   ├── __init__.py
│   ├── base.py                    # 服务基类
│   ├── memory/service.py          # 记忆服务
│   ├── chat/service.py            # 对话服务
│   ├── agent/service.py           # Agent 服务
│   ├── tool/service.py            # 工具服务
│   ├── search/service.py          # 搜索服务
│   └── model/service.py           # 模型服务
├── backend/                       # 后端
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── api/routes/stream.py   # SSE 流式端点
│       ├── core/agent_loop.py     # Agent 流水线
│       ├── db/session.py          # 数据库会话
│       └── models/memory.py       # 数据模型
├── docs/architecture/             # 架构文档 (10 份)
├── docker/nginx/default.conf      # Nginx 配置
├── docker-compose.yml             # 容器编排
└── frontend-new/                  # 前端构建产物
```