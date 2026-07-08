# Dream OS 聊天区域滚动宪法

> 状态：ACTIVE | 优先级：ABSOLUTE_PRIORITY
> 所属：Dream OS AI 执行宪法 v1.0 — 第二章补充条款

---

## 全局规则

**整个页面禁止滚动。**

禁止：
- body 滚动
- html 滚动
- 页面整体上下移动
- Header 跟随滚动
- 输入框跟随滚动

页面高度固定为：`100vh`

> ✅ 已实现：`body { overflow: hidden; height: 100vh; }`

---

## 固定区域

### 1. 顶部 Header

包含：Logo、状态栏、导航栏、模式切换按钮

**始终固定。**

> ✅ 已实现：HeaderControls `position: fixed; top: 24; right: 24;`

### 2. 底部 Input Bar

包含：输入框、发送按钮

**始终固定。**

> ✅ 已实现：InputBar 位于 flex 布局底部，不随消息滚动

---

## 唯一允许滚动区域：Conversation Stage

为整个系统唯一允许滚动的区域。

允许：
- 上下滑动消息
- 惯性滚动
- 自动滚动到底部
- 回弹效果

禁止：
- 横向滚动
- 超出边界
- 消息脱离容器

> ✅ 已实现：消息区 `overflow-y: auto; overflow-x: hidden;`

---

## 消息约束

所有消息必须存在于 Conversation Stage 内部。

禁止：
- 消息出现在 Header 区域
- 消息出现在输入框区域
- 消息出现在屏幕左上角
- 消息出现在屏幕边缘之外

> ✅ 已实现

---

## 自动滚动规则

收到新消息时：自动滚动到底部。

> ✅ 已实现：新消息触发 `scrollIntoView({ behavior: "smooth" })`

---

## 手机端体验目标

效果参考：ChatGPT / Claude / Perplexity / Apple Intelligence

用户感受：
- 整个 App 像一个固定的操作台
- 只有聊天内容在流动
- 整个世界是静止的
- 消息在中央区域流动

---

> 写入日期：2026-07-08
> 全部规则：✅ 已合规
