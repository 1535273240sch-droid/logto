# 04 - 事件流

## 事件总线设计

### Event 结构
```python
Event(
    type: str,       # 事件类型，支持通配符
    source: str,     # 事件来源
    data: Any,       # 事件数据
    priority: int,   # 优先级 (0=普通)
    timestamp: str   # ISO 时间戳
)
```

### 订阅模式
```python
bus.subscribe("agent.*", callback)       # 所有 Agent 事件
bus.subscribe("project.updated", callback)  # 项目更新
```

## 核心事件流

```
agent.start
  → brain._on_agent_event()   # 更新 last_agent
  → frontend 渲染 Agent 状态

agent.complete
  → brain.work_logs.append()  # 记录工作日志
  → frontend 更新 Agent 状态

project.updated
  → 通知所有订阅者
  → 更新项目状态摘要
```

## Living Interface 事件流

```
user.input
  → intent.classify
  → ui.decide (生长/消退/安静)
  → ui.grow / ui.shrink / ui.stay
  → task.complete
  → ui.auto_shrink
```