#!/bin/bash
# ═══════════════════════════════════════════════
# 梦幻 · Dream — 真·一键部署（从 GitHub 拉取）
# 用法: 在服务器上运行:
#   curl -fsSL https://raw.githubusercontent.com/1535273240sch-droid/logto/master/dream-os/deploy.sh | bash
#   或
#   git clone https://github.com/1535273240sch-droid/logto.git /tmp/logto && \
#   cp -r /tmp/logto/dream-os /dream-os && cd /dream-os && bash deploy.sh
# ═══════════════════════════════════════════════

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║    梦 幻 · Dream                ║"
echo "  ║    AI Operating System           ║"
echo "  ║    真·一键部署                   ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# ── 配置（可改） ──
GIT_REPO="https://github.com/1535273240sch-droid/logto.git"
DREAM_DIR="/dream-os"
BRANCH="master"

# ── 1. 检查 Docker ──
echo -e "${YELLOW}[1/6] 检查 Docker...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker 未安装，正在安装...${NC}"
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker "$(whoami)" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Docker 已安装${NC}"
else
    echo -e "${GREEN}  ✓ Docker $(docker --version | cut -d' ' -f3 | cut -d',' -f1)${NC}"
fi

if ! docker compose version &>/dev/null; then
    echo -e "${RED}Docker Compose 未安装，请手动安装:${NC}"
    echo "  sudo apt-get install docker-compose-plugin"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker Compose OK${NC}"

# ── 2. 拉取代码 ──
echo -e "${YELLOW}[2/6] 拉取代码...${NC}"
if [ -d "$DREAM_DIR/.git" ]; then
    echo "  仓库已存在，拉取更新..."
    cd "$DREAM_DIR"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    echo "  克隆仓库..."
    if [ -d "$DREAM_DIR" ]; then
        rm -rf "$DREAM_DIR"
    fi
    git clone --depth 1 -b "$BRANCH" "$GIT_REPO" "$DREAM_DIR"
    cd "$DREAM_DIR"
fi
echo -e "${GREEN}  ✓ 代码已更新${NC}"

# ── 3. 构建前端 ──
echo -e "${YELLOW}[3/6] 构建前端...${NC}"
cd "$DREAM_DIR/dream-os-next"

# 检测包管理器
if command -v pnpm &>/dev/null; then
    PM="pnpm"
elif command -v npm &>/dev/null; then
    PM="npm"
else
    echo -e "${YELLOW}  安装 Node.js 和 pnpm...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    npm install -g pnpm
    PM="pnpm"
fi

echo "  使用 $PM 安装依赖..."
$PM install --frozen-lockfile 2>/dev/null || $PM install
echo "  构建..."
$PM build
echo -e "${GREEN}  ✓ 前端构建完成${NC}"

# ── 4. 配置 .env ──
echo -e "${YELLOW}[4/6] 检查配置...${NC}"
cd "$DREAM_DIR"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}  ⚠ 已创建 .env 文件，请编辑填入你的 API Key:${NC}"
        echo -e "${YELLOW}    vim $DREAM_DIR/.env${NC}"
        echo -e "${YELLOW}  填写完成后重新运行: bash deploy.sh${NC}"
        exit 0
    else
        echo -e "${RED}.env 文件不存在，请手动创建${NC}"
        exit 1
    fi
fi

# 检查 API Key 是否仍是默认值
if grep -q "sk-your-api-key-here" .env 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ 请先编辑 .env 填入你的 AI_PROVIDER_API_KEY${NC}"
    echo -e "${YELLOW}    vim $DREAM_DIR/.env${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ .env 已配置${NC}"

# ── 5. 创建外部网络（如果不存在） ──
echo -e "${YELLOW}[5/6] 准备网络...${NC}"
docker network inspect dream-os_default &>/dev/null || docker network create dream-os_default
echo -e "${GREEN}  ✓ 网络就绪${NC}"

# ── 6. 构建并启动 ──
echo -e "${YELLOW}[6/6] 构建并启动服务（首次需要几分钟）...${NC}"
cd "$DREAM_DIR"
docker compose build --parallel 2>&1 | tail -5
docker compose up -d
sleep 3

# ── 完成 ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  部 署 完 成                              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "localhost")
echo -e "${GREEN}║  访问地址: http://${PUBLIC_IP}:3000${NC}"
echo -e "${GREEN}║  本地访问: http://localhost:3000${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  查看日志: docker compose -f $DREAM_DIR/docker-compose.yml logs -f${NC}"
echo -e "${GREEN}║  停止服务: docker compose -f $DREAM_DIR/docker-compose.yml down${NC}"
echo -e "${GREEN}║  重启服务: docker compose -f $DREAM_DIR/docker-compose.yml restart${NC}"
echo -e "${GREEN}║  更新部署: 重新运行此脚本${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# 验证
sleep 2
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务运行正常${NC}"
else
    echo -e "${YELLOW}⏳ 服务启动中，请稍候...${NC}"
    echo -e "${YELLOW}   查看状态: docker compose -f $DREAM_DIR/docker-compose.yml ps${NC}"
fi