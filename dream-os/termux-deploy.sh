#!/bin/bash
# ═══════════════════════════════════════════════
# 梦幻 · Dream — Termux 部署脚本
# 用法: 在 Termux 中运行:
#   pkg install -y curl git
#   curl -fsSL https://raw.githubusercontent.com/1535273240sch-droid/logto/master/dream-os/termux-deploy.sh | bash
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
echo "  ║    Termux 部署                   ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# ── 配置 ──
GIT_REPO="https://github.com/1535273240sch-droid/logto.git"
DREAM_DIR="$HOME/dream-os"
BRANCH="master"

# ── 1. 安装依赖 ──
echo -e "${YELLOW}[1/6] 安装系统依赖...${NC}"
pkg update -y 2>&1 | tail -1
pkg install -y python nodejs git 2>&1 | tail -3
echo -e "${GREEN}  ✓ 系统依赖安装完成${NC}"

# ── 2. 安装 pnpm ──
echo -e "${YELLOW}[2/6] 安装 pnpm...${NC}"
npm install -g pnpm 2>&1 | tail -1
echo -e "${GREEN}  ✓ pnpm 已安装${NC}"

# ── 3. 拉取代码 ──
echo -e "${YELLOW}[3/6] 拉取代码...${NC}"
if [ -d "$DREAM_DIR/.git" ]; then
    echo "  仓库已存在，拉取更新..."
    cd "$DREAM_DIR"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
else
    if [ -d "$DREAM_DIR" ]; then
        rm -rf "$DREAM_DIR"
    fi
    git clone --depth 1 -b "$BRANCH" "$GIT_REPO" "$DREAM_DIR"
fi
echo -e "${GREEN}  ✓ 代码已拉取到 $DREAM_DIR${NC}"

# ── 4. 配置 .env ──
echo -e "${YELLOW}[4/6] 检查配置...${NC}"
cd "$DREAM_DIR"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}  ╔══════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}  ║  请编辑 .env 文件填入你的 API Key        ║${NC}"
        echo -e "${YELLOW}  ║                                        ║${NC}"
        echo -e "${YELLOW}  ║  nano $DREAM_DIR/.env                 ║${NC}"
        echo -e "${YELLOW}  ║  修改 AI_PROVIDER_API_KEY 为你自己的     ║${NC}"
        echo -e "${YELLOW}  ║  然后重新运行: bash termux-deploy.sh   ║${NC}"
        echo -e "${YELLOW}  ╚══════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}.env 文件不存在${NC}"
        exit 1
    fi
fi

# 检查 API Key 是否仍是默认值
if grep -q "sk-your-api-key-here" .env 2>/dev/null; then
    echo -e "${YELLOW}  ╔══════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}  ║  请先编辑 .env 填入你的 API Key         ║${NC}"
    echo -e "${YELLOW}  ║  nano $DREAM_DIR/.env                  ║${NC}"
    echo -e "${YELLOW}  ║  修改 AI_PROVIDER_API_KEY 为你自己的     ║${NC}"
    echo -e "${YELLOW}  ║  然后重新运行: bash termux-deploy.sh   ║${NC}"
    echo -e "${YELLOW}  ╚══════════════════════════════════════════╝${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ .env 已配置${NC}"

# 加载环境变量
set -a
source .env
set +a

# ── 5. 构建前端 ──
echo -e "${YELLOW}[5/6] 构建前端...${NC}"
cd "$DREAM_DIR/dream-os-next"
echo "  安装依赖..."
pnpm install 2>&1 | tail -2
echo "  构建..."
pnpm build 2>&1 | tail -5
echo -e "${GREEN}  ✓ 前端构建完成${NC}"

# ── 6. 安装后端依赖并启动 ──
echo -e "${YELLOW}[6/6] 安装后端依赖并启动服务...${NC}"
cd "$DREAM_DIR/backend"
pip install -r requirements.txt 2>&1 | tail -2

# 设置 Python 路径
export PYTHONPATH="$DREAM_DIR/backend:$DREAM_DIR/core:$DREAM_DIR/services:$PYTHONPATH"

# 启动后端
echo "  启动后端 (端口 8000)..."
cd "$DREAM_DIR/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 启动前端
echo "  启动前端 (端口 3000)..."
cd "$DREAM_DIR/dream-os-next"
python3 -m http.server 3000 --directory dist &
FRONTEND_PID=$!

cd "$DREAM_DIR"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  部 署 完 成                              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  前端地址: http://localhost:3000          ║${NC}"
echo -e "${GREEN}║  后端地址: http://localhost:8000/api      ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  停止服务:                                ║${NC}"
echo -e "${GREEN}║    kill $BACKEND_PID $FRONTEND_PID        ║${NC}"
echo -e "${GREEN}║  或重启 Termux 后重新运行脚本              ║${NC}"
echo -e "${GREEN}║                                          ║${NC}"
echo -e "${GREEN}║  更新: 重新运行此脚本即可                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# 验证后端
sleep 3
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端运行正常${NC}"
else
    echo -e "${YELLOW}⏳ 后端启动中...${NC}"
fi
echo -e "${GREEN}✅ 前端已启动${NC}"

# 保持脚本运行
wait