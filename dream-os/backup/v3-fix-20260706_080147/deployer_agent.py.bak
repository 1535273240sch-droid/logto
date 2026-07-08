"""Deployer Agent — 部署到测试环境

负责:
  - 生成 Docker 配置 (Dockerfile / docker-compose.yml)
  - 部署到测试环境
  - 健康检查
  - 返回访问地址
"""
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class DeployerAgent(BaseAgent):
    """部署到测试环境"""

    role = "deployer"
    name = "部署员"
    emoji = "🚀"
    description = "生成 Docker 配置、部署到测试环境、健康检查"
    allowed_tools = ["shell_exec", "file_read"]
    max_iterations = 8
    temperature = 0.2

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的部署员 (Deployer Agent)。

## 你的职责
将项目部署到测试环境，确保可访问。

## 部署策略 (按优先级)
1. **直接运行**: 如果是 Python 项目，直接 python src/main.py 后台运行
2. **Docker**: 如果有 Dockerfile，构建并运行容器
3. **简单部署**: 不需要复杂配置，确保项目能跑起来即可

## 工作流程
1. 查看项目结构: ls -la src/
2. 确定入口文件和运行命令
3. 安装缺失依赖: pip install flask fastapi uvicorn ...
4. 后台启动项目: nohup python src/main.py > logs/run.log 2>&1 &
5. 等待几秒后检查: curl http://localhost:{port}/
6. 记录访问地址和端口

## 端口分配
- 使用 8000-9000 范围内的端口
- 避免与已有服务冲突: 先 ss -tlnp | grep :8000

## 输出格式 (JSON)
```json
{
  "deployed": true/false,
  "method": "direct/docker",
  "url": "http://localhost:8000",
  "port": 8000,
  "pid": 12345,
  "health_check": "passed/failed",
  "startup_log": "启动日志摘要",
  "errors": ["如果有错误"]
}
```

## 重要
- 部署是到测试环境，不是生产环境
- 如果部署失败，记录原因
- 不要修改代码，只做部署相关操作"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        deploy_data = result.data if result.data else {"raw_output": result.output}
        blackboard.deployment = deploy_data
        blackboard.update("deployer", "deployment", deploy_data)
