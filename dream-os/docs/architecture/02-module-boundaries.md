# 02 - 模块边界

## 模块划分

### Core (不可变)
- `event_bus.py` - 事件总线
- `quality_guardian/` - 质量门禁
- `project_brain/` - 项目状态

### Services (可扩展)
- `memory/` - 记忆管理
- `chat/` - 对话管理
- `agent/` - Agent 执行
- `tool/` - 工具注册
- `search/` - 搜索服务
- `model/` - 模型管理

### Features (可组合)
- `chat/` - 聊天功能
- `dev/` - 开发模式
- `project/` - 项目管理

### Components (可复用)
- Button, Input, Message, Modal, Toast, Card, Toolbar, Sidebar

### Pages (路由层)
- Home (Living Interface 首页)

## 通信规则

1. 模块间不直接 import
2. 通过 EventBus 发布/订阅事件
3. Service 层通过惰性导入对接真实模块
4. Feature 通过 API 与服务通信

## Living Interface 边界

- 页面不预设组件
- Agent 面板按需生长
- 任务完成后自动消退
- 模型切换面板可伸缩