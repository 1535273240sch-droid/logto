#!/bin/bash
# ═══════════════════════════════════════════════
# 梦幻 · Dream — 本地部署（无需 Docker）
# 用法: bash local-deploy.sh
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
echo "  ║    本地部署（无 Docker）          ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

DREAM_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1. 检查依赖 ──
echo -e "${YELLOW}[1/5] 检查依赖...${NC}"

# Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Python $(python3 --version | cut -d' ' -f2)${NC}"

# Node.js
if ! command -v node &>/dev/null; then
    echo -e "${RED}Node.js 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Node $(node --version)${NC}"

# pnpm
if ! command -v pnpm &>/dev/null; then
    echo -e "${YELLOW}  安装 pnpm...${NC}"
    npm install -g pnpm
fi
echo -e "${GREEN}  ✓ pnpm OK${NC}"

# ── 2. 配置 .env ──
echo -e "${YELLOW}[2/5] 检查配置...${NC}"
cd "$DREAM_DIR"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}  ⚠ 已创建 .env 文件，请编辑填入你的 API Key:${NC}"
        echo -e "${YELLOW}    vim $DREAM_DIR/.env${NC}"
        echo -e "${YELLOW}  填写完成后重新运行: bash local-deploy.sh${NC}"
        exit 0
    else
        echo -e "${RED}.env 文件不存在${NC}"
        exit 1
    fi
fi

if grep -q "sk-your-api-key-here" .env 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ 请先编辑 .env 填入你的 AI_PROVIDER_API_KEY${NC}"
    echo -e "${YELLOW}    vim $DREAM_DIR/.env${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ .env 已配置${NC}"

# 加载环境变量
set -a
source .env
set +a

# ── 3. 构建前端 ──
echo -e "${YELLOW}[3/5] 构建前端...${NC}"
cd "$DREAM_DIR/dream-os-next"

echo "  安装依赖..."
pnpm install 2>&1 | tail -2
echo "  构建..."
pnpm build 2>&1 | tail -5
echo -e "${GREEN}  ✓ 前端构建完成${NC}"

# ── 4. 安装后端依赖 ──
echo -e "${YELLOW}[4/5] 安装后端依赖...${NC}"
cd "$DREAM_DIR/backend"
pip3 install -r requirements.txt 2>&1 | tail -2
echo -e "${GREEN}  ✓ 后端依赖安装完成${NC}"

# ── 5. 启动服务 ──
echo -e "${YELLOW}[5/5] 启动服务...${NC}"
cd "$DREAM_DIR"

# 设置 Python 路径
export PYTHONPATH="$(pwd)/backend:$(pwd)/core:$(pwd)/services:$PYTHONPATH"

# 启动后端（后台）
echo "  启动后端 (端口 8000)..."
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd "$DREAM_DIR"

# 启动前端（后台）
echo "  启动前端 (端口 3000)..."
cd dream-os-next
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
echo -e "${GREEN}║  停止服务: kill $BACKEND_PID $FRONTEND_PID${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# 等待后端启动
sleep 2
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端运行正常${NC}"
else
    echo -e "${YELLOW}⏳ 后端启动中...${NC}"
fi

echo -e "${GREEN}✅ 前端已启动${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"

# 等待子进程
wait