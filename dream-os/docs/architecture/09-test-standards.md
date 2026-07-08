# 09 - 测试规范

## 回归测试模块 (17 个)

1. chat - 对话功能
2. search - 搜索功能
3. image - 图片功能
4. file_upload - 文件上传
5. memory - 记忆管理
6. agent - Agent 执行
7. workflow - 工作流
8. project - 项目管理
9. chart - 图表
10. mermaid - 流程图
11. ppt - PPT 生成
12. markdown - Markdown 渲染
13. api - API 接口
14. database - 数据库
15. home - 首页
16. execution_mode - 执行模式
17. dev_mode - 开发模式

## Quality Guardian 规则 (12 条)

- CQ-001: 语法检查
- CQ-002: 文件大小限制
- CQ-003: 行长度限制
- ARC-001: 架构层级检查
- ARC-002: 模块边界检查
- DS-001: 设计系统合规
- CD-001: 循环依赖检查
- RG-001: 回归测试通过
- API-001: API 契约检查
- DB-001: 数据库迁移检查
- PF-001: 性能基准
- SC-001: 安全扫描
- ST-001: 稳定性检查

## 修复循环

最多 3 次修复，失败后生成带具体修复建议的报告。