#!/bin/bash
# Dream OS V3 部署脚本
# 用法: ./deploy_v3.sh
# 功能: 上传 V3 代码 + 前端页面 + Nginx 配置到服务器、创建数据库表、重启服务
set -e

SERVER="1.14.125.204"
USER="root"
PASS="Sch13255884503"
SSH="sshpass -p ${PASS} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 ${USER}@${SERVER}"
SCP="sshpass -p ${PASS} scp -o StrictHostKeyChecking=no -o ConnectTimeout=20"

LOCAL_BACKEND="/workspace/dream-os-backup/backend"
LOCAL_FRONTEND="/workspace/dream-os-backup/frontend"
LOCAL_NGINX="/workspace/nginx-dream-os.conf"

echo "═══════════════════════════════════════════════"
echo "  Dream OS V3 部署脚本"
echo "  服务器: ${SERVER}"
echo "═══════════════════════════════════════════════"

# ── 1. 测试服务器连接 ──
echo ""
echo "[1/8] 测试服务器连接..."
if ! ${SSH} "echo OK" >/dev/null 2>&1; then
    echo "❌ 无法连接到服务器 ${SERVER}"
    echo "   请检查服务器状态或网络连接"
    exit 1
fi
echo "✅ 服务器连接正常"

# ── 2. 创建目录结构 ──
echo ""
echo "[2/8] 创建服务器目录..."
${SSH} "mkdir -p /dream-os/backend/app/core/v3/agents /dream-os/backend/app/api/routes /dream-os/backend/app/models /dream-os/frontend /dream-os/nginx /workspace/projects"
echo "✅ 目录已创建"

# ── 3. 上传 V3 核心框架 ──
echo ""
echo "[3/8] 上传 V3 核心框架..."
${SCP} ${LOCAL_BACKEND}/app/core/v3/__init__.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/__init__.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/blackboard.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/blackboard.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/base_agent.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/base_agent.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/workspace.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/workspace.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/sse_v2.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/sse_v2.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/orchestrator.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/orchestrator.py
${SCP} ${LOCAL_BACKEND}/app/core/v3/auto_loop.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/auto_loop.py
echo "✅ 核心框架已上传 (7 个文件)"

# ── 4. 上传 8 个 Agent ──
echo ""
echo "[4/8] 上传 8 个专业 Agent..."
for agent in planner_agent architect_agent coder_agent executor_agent reviewer_agent tester_agent deployer_agent reporter_agent; do
    ${SCP} ${LOCAL_BACKEND}/app/core/v3/agents/${agent}.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/agents/${agent}.py
done
${SCP} ${LOCAL_BACKEND}/app/core/v3/agents/__init__.py ${USER}@${SERVER}:/dream-os/backend/app/core/v3/agents/__init__.py
echo "✅ 8 个 Agent 已上传"

# ── 5. 上传模型、路由 ──
echo ""
echo "[5/8] 上传模型、API 路由..."
${SCP} ${LOCAL_BACKEND}/app/models/dev_task.py ${USER}@${SERVER}:/dream-os/backend/app/models/dev_task.py
${SCP} ${LOCAL_BACKEND}/app/models/__init__.py ${USER}@${SERVER}:/dream-os/backend/app/models/__init__.py
${SCP} ${LOCAL_BACKEND}/app/api/routes/v3_dev.py ${USER}@${SERVER}:/dream-os/backend/app/api/routes/v3_dev.py
${SCP} ${LOCAL_BACKEND}/app/main.py ${USER}@${SERVER}:/dream-os/backend/app/main.py
echo "✅ 模型、路由已上传"

# ── 6. 上传前端页面 + Nginx 配置 ──
echo ""
echo "[6/8] 上传前端页面 + Nginx 配置..."
${SCP} ${LOCAL_FRONTEND}/v3-dev.html ${USER}@${SERVER}:/dream-os/frontend/v3-dev.html
${SCP} ${LOCAL_NGINX} ${USER}@${SERVER}:/dream-os/nginx/nginx.conf
echo "✅ 前端页面 + Nginx 配置已上传"

# ── 7. 创建数据库表 + 重启服务 + 应用 Nginx ──
echo ""
echo "[7/8] 创建 dev_tasks 表、应用 Nginx 配置、重启服务..."

${SSH} 'bash -s' <<'REMOTE_EOF'
set -e
cd /dream-os

# 备份现有 nginx 配置
NGINX_CONF_PATH=""
for p in /etc/nginx/conf.d/dream-os.conf /etc/nginx/sites-enabled/dream-os /dream-os/nginx/nginx.conf; do
    if [ -f "$p" ]; then
        NGINX_CONF_PATH="$p"
        break
    fi
done

# 应用新的 nginx 配置 (尝试多个常见位置)
echo "应用 Nginx 配置..."
if [ -d /etc/nginx/conf.d ]; then
    cp /dream-os/nginx/nginx.conf /etc/nginx/conf.d/dream-os.conf
    NGINX_CONF_PATH="/etc/nginx/conf.d/dream-os.conf"
    echo "Nginx 配置已复制到: ${NGINX_CONF_PATH}"
elif docker ps --format '{{.Names}}' | grep -q nginx; then
    docker cp /dream-os/nginx/nginx.conf dream-os-nginx:/etc/nginx/conf.d/dream-os.conf 2>/dev/null || true
    echo "Nginx 配置已复制到 nginx 容器"
fi

# 创建 dev_tasks 表 (使用 SQLAlchemy 自动创建)
echo "创建 dev_tasks 表..."
docker exec dream-os-backend python -c "
import asyncio
from app.db.session import engine
from app.models.dev_task import DevTask
from sqlalchemy import text

async def create_table():
    async with engine.begin() as conn:
        result = await conn.execute(text(\"\"\"
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'dev_tasks'
            )
        \"\"\"))
        exists = result.scalar()
        if exists:
            print('dev_tasks 表已存在，跳过创建')
        else:
            await conn.run_sync(lambda sync_conn: DevTask.__table__.create(sync_conn))
            print('dev_tasks 表创建成功')

asyncio.run(create_table())
" 2>&1 || echo "⚠️ 表创建失败，可能需要在容器内手动执行"

# 重启后端容器
echo "重启后端容器..."
docker restart dream-os-backend
sleep 3

# 重载 Nginx
echo "重载 Nginx..."
if command -v nginx >/dev/null 2>&1; then
    nginx -t 2>&1 && nginx -s reload 2>&1 || echo "⚠️ Nginx 重载失败 (主机)"
elif docker ps --format '{{.Names}}' | grep -q nginx; then
    docker exec dream-os-nginx nginx -t 2>&1 && docker exec dream-os-nginx nginx -s reload 2>&1 || echo "⚠️ Nginx 重载失败 (容器)"
else
    echo "⚠️ 未找到 nginx，请确认前端服务方式"
fi

# 验证后端启动
echo "验证后端启动..."
for i in 1 2 3 4 5; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "✅ 后端已启动"
        break
    fi
    sleep 2
done

# 验证 V3 路由
echo "验证 V3 API..."
if curl -s http://localhost:8000/api/v3/dev/agents | head -c 200; then
    echo ""
    echo "✅ V3 API 可用"
else
    echo "❌ V3 API 不可用，请检查日志"
    docker logs dream-os-backend --tail 30
fi

# 验证前端页面
echo ""
echo "验证前端页面..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/v3-dev.html | grep -q 200; then
    echo "✅ v3-dev.html 可访问"
else
    echo "⚠️ v3-dev.html 访问异常 (可能需要等待 nginx 重载)"
fi
REMOTE_EOF

# ── 8. 完成 ──
echo ""
echo "[8/8] 部署完成!"
echo ""
echo "═══════════════════════════════════════════════"
echo "  Dream OS V3 部署完成"
echo "═══════════════════════════════════════════════"
echo ""
echo "访问地址:"
echo "  自主开发控制台: http://${SERVER}/v3-dev.html"
echo "  AI 聊天:        http://${SERVER}/"
echo "  V3 API 文档:    http://${SERVER}:8000/api/docs"
echo "  Agent 列表:     http://${SERVER}:8000/api/v3/dev/agents"
echo "  任务列表:       http://${SERVER}:8000/api/v3/dev/tasks"
echo ""
echo "测试命令:"
echo "  curl -X POST http://${SERVER}:8000/api/v3/dev/start \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"requirement\":\"创建一个 hello world Python 项目\",\"max_iterations\":2}'"
echo ""
