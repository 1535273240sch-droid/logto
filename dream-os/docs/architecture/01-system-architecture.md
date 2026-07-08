# 01 - 系统架构

## 概述
Dream OS V6 采用五层架构设计，从系统核心到用户界面逐层抽象。

## 五层架构

```
Layer 5: Pages          (页面层 - 用户可见)
Layer 4: Features       (功能层 - 组合组件)
Layer 3: Components     (组件层 - 可复用 UI)
Layer 2: Services       (服务层 - 业务逻辑)
Layer 1: Core           (核心层 - 不可修改)
```

## 层间规则

1. **单向依赖**：上层可以依赖下层，禁止反向依赖
2. **跨层禁止**：Layer 5 不能直接调用 Layer 1，必须经过 Layer 2/3/4
3. **Event Bus 通信**：模块间禁止直接调用，全部通过 EventBus 发布/订阅
4. **Core 只读**：Core 层以 `:ro` 挂载，任何 Agent 不可修改

## 核心模块

- **EventBus**: 单例事件总线，支持通配符订阅
- **Quality Guardian**: 系统级质量门禁，12 条规则 + 17 模块回归
- **Project Brain**: 项目状态内核，Agent 接力，30 秒规则

## Living Interface 原则

- 界面不是预先设计好的，而是随着用户目标自然生长
- 用户说"聊天"→ 保持安静模式
- 用户说"开发"→ 8-Agent 流水线生长
- 用户说"做PPT"→ Artifact 区域生长
- 任务完成后自动消退