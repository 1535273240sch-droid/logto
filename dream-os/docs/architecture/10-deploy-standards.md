# 10 - 部署规范

## Docker 部署

### 前端 (Nginx)
- 静态文件: `frontend-new/` 挂载到 `/usr/share/nginx/html`
- 配置: `docker/nginx/default.conf`
- API 代理: `/api/*` → backend:8000
- SSE 流式: 关闭缓冲

### 后端 (FastAPI)
- 端口: 8000
- Core 只读挂载: `./core:/dream-os/core:ro`
- Services 只读挂载: `./services:/dream-os/services:ro`
- PYTHONPATH: `/app:/dream-os`

### 网络
- dream-os-net bridge 网络

## 启动命令

```bash
docker-compose up -d
```

## 验证

```bash
curl http://localhost:3000/         # 前端
curl http://localhost:8000/api/health  # 后端
```

## 安全规则

1. Core 和 Services 只读挂载
2. 任何 Agent 不可修改 Core/Service 代码
3. 前端静态文件部署后不可被后端修改
4. 数据库仅通过 API 访问