# 03 - 数据流

## 通信方式

### SSE 流式 (Server-Sent Events)
- 端点: `POST /api/chat/stream`
- chat 模式: 10 步 Agent Pipeline
- dev 模式: 8-Agent 流水线

### EventBus 事件
- 模块间通过 EventBus 发布/订阅
- 支持通配符 `*` 订阅
- 事件类型: `agent.start`, `agent.complete`, `project.updated`

### 数据库
- SQLite (async via aiosqlite)
- 模型: Conversation, Message, Memory

## 流式数据事件

### dev 模式事件
```
dev_start → agent_start(planner) → agent_complete → agent_start(architect) → ... → dev_complete
```

### chat 模式事件
```
content → content → content → done
```

## Living Interface 数据流

1. 用户输入 → 意图分类
2. 意图分类 → UI 决策
3. UI 决策 → 界面生长/消退
4. 任务完成 → 状态更新 → 自动消退