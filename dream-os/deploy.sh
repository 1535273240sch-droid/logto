#!/bin/bash
# ═══════════════════════════════════════════
# 梦幻 · Dream — 真·一键部署
# 用法: curl ... | bash  或  ./deploy.sh
# ═══════════════════════════════════════════

set -e

echo "梦幻 · Dream 部署中..."

# 1. 检查 Docker
command -v docker &>/dev/null || { echo "请先装Docker: curl -fsSL https://get.docker.com | bash"; exit 1; }

# 2. 从服务器拉取项目包
SOURCE=${DREAM_SOURCE:-1.14.125.204}
echo "从 $SOURCE 拉取项目..."
ssh -o StrictHostKeyChecking=no ubuntu@$SOURCE "cd /dream-os && tar czf /tmp/dream-os.tar.gz ." 2>/dev/null
scp ubuntu@$SOURCE:/tmp/dream-os.tar.gz .

# 3. 解压
mkdir -p dream-os && tar xzf dream-os.tar.gz -C dream-os && cd dream-os

# 4. 首次自动生成 .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 填入 API Key: vim .env"
    echo "改完运行: docker compose up -d"
    exit 0
fi

# 5. 构建启动
docker compose up -d --build
echo "✅ 部署完成！访问 http://localhost"
