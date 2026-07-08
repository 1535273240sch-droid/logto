# 05 - 状态管理

## 项目状态 (ProjectState)

```python
ProjectState(
    project_id: str,
    name: str,
    phase: str,              # 当前阶段
    progress_percent: int,   # 进度百分比
    completed_tasks: List,   # 已完成任务
    pending_tasks: List,     # 待处理任务
    bugs: List,              # BUG 列表
    risks: List,             # 风险列表
    deploy_status: str,      # 部署状态
    last_agent: str,         # 最后执行的 Agent
    last_updated: str,       # 最后更新时间
)
```

## 前端状态

### 页面模式
- `chat`: 对话模式（安静，无 Agent 面板）
- `dev`: 开发模式（Agent 流水线生长）
- `quiet`: 初始状态（空页面）

### Agent 状态
- `idle`: 空闲
- `running`: 执行中
- `done`: 完成

## 状态持久化

- Project Brain 支持 save/load
- 数据存储在 `/workspace/dream-os/data/`
- 工作日志最多保留 100 条

## Living Interface 状态

- 界面状态由 AI 意图推理驱动
- 不预设面板状态
- 页面组件按需生长/消退