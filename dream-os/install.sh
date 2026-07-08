#!/bin/bash
set -e

# ═══════════════════════════════════════════
# 梦幻 · Dream — 一键部署脚本
# ═══════════════════════════════════════════

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║    梦 幻 · Dream                ║"
echo "  ║    AI Operating System           ║"
echo "  ║    一键部署脚本 v1.0              ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# ── 1. 检查 Docker ──
echo -e "${YELLOW}[1/4] 检查 Docker...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker 未安装，请先安装 Docker:${NC}"
    echo "  curl -fsSL https://get.docker.com | bash"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker $(docker --version | cut -d' ' -f3 | cut -d',' -f1)${NC}"

if ! docker compose version &>/dev/null; then
    echo -e "${RED}Docker Compose 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker Compose OK${NC}"

# ── 2. 检查 .env ──
echo -e "${YELLOW}[2/4] 检查配置...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}  ⚠ 已创建 .env 文件，请编辑填入你的 API Key:${NC}"
        echo -e "${YELLOW}    vim .env${NC}"
        echo -e "${YELLOW}  填写完成后重新运行: ./install.sh${NC}"
        exit 0
    else
        echo -e "${RED}.env 和 .env.example 都不存在${NC}"
        exit 1
    fi
fi

# 检查 API Key 是否填写
if grep -q "sk-your-api-key-here" .env 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ 请先编辑 .env 填入你的 AI_PROVIDER_API_KEY${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ .env 已配置${NC}"

# ── 3. 构建镜像 ──
echo -e "${YELLOW}[3/4] 构建镜像（首次需要几分钟）...${NC}"
docker compose build --parallel 2>&1 | tail -5
echo -e "${GREEN}  ✓ 构建完成${NC}"

# ── 4. 启动服务 ──
echo -e "${YELLOW}[4/4] 启动服务...${NC}"
docker compose up -d
sleep 3

# ── 检查 ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  部 署 完 成                              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"

# 获取公网IP（如果有）
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "localhost")
echo -e "${GREEN}║  访问地址: http://${PUBLIC_IP}${NC}"

# 本地也是 localhost
if [ "$PUBLIC_IP" != "localhost" ]; then
    echo -e "${GREEN}║  本地访问: http://localhost${NC}"
fi

echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  查看日志: docker compose logs -f backend${NC}"
echo -e "${GREEN}║  停止服务: docker compose down${NC}"
echo -e "${GREEN}║  重启服务: docker compose restart${NC}"
echo -e "${GREEN}║  切换模型: 访问页面 → 模型设置${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# 验证服务
sleep 2
if curl -s http://localhost/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务运行正常${NC}"
else
    echo -e "${YELLOW}⏳ 服务启动中，请稍候...${NC}"
    echo -e "${YELLOW}   查看状态: docker compose ps${NC}"
fi
