#!/bin/bash
set -euo pipefail

# ============================================================
# Logto 从源码构建一键部署脚本
# 功能：从 GitHub 仓库拉取源码，用 Dockerfile 构建镜像，Docker Compose 部署
# 用法：
#   ./deploy-from-source.sh              # 一键构建部署
#   ./deploy-from-source.sh start        # 启动服务
#   ./deploy-from-source.sh stop         # 停止服务
#   ./deploy-from-source.sh restart      # 重启服务
#   ./deploy-from-source.sh logs         # 查看日志
#   ./deploy-from-source.sh update       # 拉取最新代码并重新构建部署
#   ./deploy-from-source.sh rebuild      # 强制重新构建镜像
#   ./deploy-from-source.sh down         # 停止并移除容器
#   ./deploy-from-source.sh status       # 查看状态
# ============================================================

# ---------- 配置 ----------
PROJECT_NAME="logto"
DEPLOY_DIR="${DEPLOY_DIR:-$HOME/logto-source}"
SRC_DIR="$DEPLOY_DIR/src"
LOG_DIR="$HOME/.local/var/log/logto-source"
DEPLOY_LOG="$LOG_DIR/deploy.log"
ENV_FILE="$DEPLOY_DIR/.env"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"

# 仓库配置
GIT_REPO="${GIT_REPO:-https://github.com/1535273240sch-droid/logto.git}"
GIT_BRANCH="${GIT_BRANCH:-master}"

# 镜像配置
IMAGE_NAME="${IMAGE_NAME:-logto-custom}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:17-alpine}"

# 端口配置
PORT_USER="${PORT_USER:-3001}"
PORT_ADMIN="${PORT_ADMIN:-3002}"

# 数据库配置
DB_USER="${DB_USER:-logto}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-logto}"

# Logto 配置
ENDPOINT="${ENDPOINT:-}"
ADMIN_ENDPOINT="${ADMIN_ENDPOINT:-}"
TRUST_PROXY_HEADER="${TRUST_PROXY_HEADER:-1}"

# 构建配置
BUILD_NO_CACHE="${BUILD_NO_CACHE:-0}"

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------- 日志函数 ----------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" || true
    [ -f "$DEPLOY_LOG" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" >> "$DEPLOY_LOG" || true
    return 0
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*" || true
    [ -f "$DEPLOY_LOG" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OK] $*" >> "$DEPLOY_LOG" || true
    return 0
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" || true
    [ -f "$DEPLOY_LOG" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >> "$DEPLOY_LOG" || true
    return 0
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2 || true
    [ -f "$DEPLOY_LOG" ] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >> "$DEPLOY_LOG" || true
    return 0
}

# ---------- 工具函数 ----------
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

generate_password() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24
}

# ---------- 初始化日志 ----------
init_logging() {
    mkdir -p "$(dirname "$DEPLOY_LOG")" 2>/dev/null || true
    : > "$DEPLOY_LOG" 2>/dev/null || true
    return 0
}

# ---------- 检查环境 ----------
check_environment() {
    log_info "检查环境依赖..."

    # Docker
    if command_exists docker; then
        log_success "Docker: $(docker --version)"
    else
        log_error "Docker 未安装，请先安装 Docker"
        log_info "参考: https://docs.docker.com/engine/install/"
        exit 1
    fi

    # Docker Compose
    if docker compose version >/dev/null 2>&1; then
        log_success "Docker Compose: $(docker compose version --short)"
    else
        log_error "Docker Compose 不可用"
        exit 1
    fi

    # Git
    if command_exists git; then
        log_success "Git: $(git --version)"
    else
        log_warn "Git 未安装，尝试自动安装..."
        install_git
    fi

    # Docker 权限
    if ! docker info >/dev/null 2>&1; then
        log_warn "当前用户可能没有 Docker 权限，尝试使用 sudo..."
        if command_exists sudo && sudo docker info >/dev/null 2>&1; then
            alias docker='sudo docker'
            log_success "已切换为 sudo docker 模式"
        else
            log_error "无法访问 Docker 守护进程"
            exit 1
        fi
    fi
}

install_git() {
    local os_type
    os_type="$(. /etc/os-release && echo "$ID")"

    case "$os_type" in
        ubuntu|debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq git
            ;;
        centos|rhel|rocky|almalinux)
            sudo yum install -y -q git
            ;;
        *)
            log_error "不支持的操作系统: $os_type，请手动安装 Git"
            exit 1
            ;;
    esac
    log_success "Git 安装完成"
}

# ---------- 拉取/更新源码 ----------
fetch_source() {
    if [ -d "$SRC_DIR/.git" ]; then
        log_info "更新已有代码仓库..."
        cd "$SRC_DIR"

        local current_branch
        current_branch="$(git rev-parse --abbrev-ref HEAD)"

        if [ "$current_branch" != "$GIT_BRANCH" ]; then
            log_info "切换分支: $current_branch -> $GIT_BRANCH"
            git fetch origin
            git checkout "$GIT_BRANCH"
        fi

        local before_hash after_hash
        before_hash="$(git rev-parse HEAD)"
        git pull origin "$GIT_BRANCH"
        after_hash="$(git rev-parse HEAD)"

        if [ "$before_hash" = "$after_hash" ]; then
            log_info "代码已是最新 (commit: ${after_hash:0:7})"
            return 1
        else
            log_success "代码已更新: ${before_hash:0:7} -> ${after_hash:0:7}"
            return 0
        fi
    else
        log_info "克隆仓库: $GIT_REPO (分支: $GIT_BRANCH)"
        mkdir -p "$(dirname "$SRC_DIR")"
        git clone --depth 1 --branch "$GIT_BRANCH" "$GIT_REPO" "$SRC_DIR"
        log_success "代码克隆完成"
        return 0
    fi
}

# ---------- 构建镜像 ----------
build_image() {
    log_info "构建 Docker 镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
    log_info "这可能需要 5-15 分钟，请耐心等待..."

    cd "$SRC_DIR"

    local build_args=""
    if [ "$BUILD_NO_CACHE" = "1" ]; then
        build_args="--no-cache"
        log_warn "使用 --no-cache 模式构建（无缓存，耗时更长）"
    fi

    docker build $build_args \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -f Dockerfile \
        .

    log_success "镜像构建完成: ${IMAGE_NAME}:${IMAGE_TAG}"
}

# ---------- 创建部署目录 ----------
prepare_deploy_dir() {
    mkdir -p "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR/data/postgres"
    mkdir -p "$DEPLOY_DIR/data/logto"
}

# ---------- 生成 docker-compose.yml ----------
generate_compose_file() {
    log_info "生成 docker-compose.yml..."

    cat > "$COMPOSE_FILE" << 'EOF'
services:
  postgres:
    image: ${POSTGRES_IMAGE}
    container_name: ${PROJECT_NAME}-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - logto-net

  logto:
    image: ${IMAGE_NAME}:${IMAGE_TAG}
    container_name: ${PROJECT_NAME}-app
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "${PORT_USER}:3001"
      - "${PORT_ADMIN}:3002"
    environment:
      - DB_URL=postgres://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - TRUST_PROXY_HEADER=${TRUST_PROXY_HEADER}
      - ENDPOINT=${ENDPOINT}
      - ADMIN_ENDPOINT=${ADMIN_ENDPOINT}
      - PRIVATE_KEY_ROTATION_GRACE_PERIOD=${PRIVATE_KEY_ROTATION_GRACE_PERIOD:-0}
    volumes:
      - ./data/logto:/etc/logto/packages/cli/alteration-scripts
    entrypoint: ["sh", "-c"]
    command:
      - |
        if [ ! -f /etc/logto/.initialized ]; then
          echo "First run: seeding database..."
          npm run cli db seed -- --swe && touch /etc/logto/.initialized
        fi
        npm start
    networks:
      - logto-net

networks:
  logto-net:
    driver: bridge
EOF

    log_success "docker-compose.yml 已生成"
}

# ---------- 生成 .env 文件 ----------
generate_env_file() {
    if [ -f "$ENV_FILE" ]; then
        log_info ".env 文件已存在，跳过生成"
        return 0
    fi

    log_info "生成 .env 配置文件..."

    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD="$(generate_password)"
        log_info "已自动生成数据库密码"
    fi

    cat > "$ENV_FILE" << EOF
# ============================================================
# Logto 源码构建部署配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

# 项目配置
PROJECT_NAME=${PROJECT_NAME}

# 镜像配置
IMAGE_NAME=${IMAGE_NAME}
IMAGE_TAG=${IMAGE_TAG}
POSTGRES_IMAGE=${POSTGRES_IMAGE}

# 源码仓库配置
GIT_REPO=${GIT_REPO}
GIT_BRANCH=${GIT_BRANCH}

# 端口配置
PORT_USER=${PORT_USER}
PORT_ADMIN=${PORT_ADMIN}

# 数据库配置
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}

# Logto 配置
# 正式使用时请修改为你的实际域名
# ENDPOINT=https://auth.yourdomain.com
# ADMIN_ENDPOINT=https://admin.yourdomain.com
ENDPOINT=${ENDPOINT}
ADMIN_ENDPOINT=${ADMIN_ENDPOINT}
TRUST_PROXY_HEADER=${TRUST_PROXY_HEADER}

# 高级配置
PRIVATE_KEY_ROTATION_GRACE_PERIOD=0
EOF

    log_success ".env 文件已生成: $ENV_FILE"
}

# ---------- 加载 .env ----------
load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        # shellcheck disable=SC1090
        . "$ENV_FILE"
        set +a
    fi
}

# ---------- 启动服务 ----------
start_services() {
    log_info "启动 Logto 服务..."
    cd "$DEPLOY_DIR"
    docker compose up -d
    log_success "服务已启动"
}

# ---------- 停止服务 ----------
stop_services() {
    log_info "停止 Logto 服务..."
    cd "$DEPLOY_DIR"
    docker compose stop
    log_success "服务已停止"
}

# ---------- 重启服务 ----------
restart_services() {
    log_info "重启 Logto 服务..."
    cd "$DEPLOY_DIR"
    docker compose restart
    log_success "服务已重启"
}

# ---------- 查看日志 ----------
show_logs() {
    cd "$DEPLOY_DIR"
    docker compose logs -f --tail=100 "$@"
}

# ---------- 查看状态 ----------
show_status() {
    log_info "服务状态:"
    cd "$DEPLOY_DIR"
    docker compose ps
    echo ""
    log_info "部署目录: $DEPLOY_DIR"
    log_info "源码目录: $SRC_DIR"
    log_info "日志文件: $DEPLOY_LOG"

    if [ -d "$SRC_DIR/.git" ]; then
        cd "$SRC_DIR"
        local hash branch
        hash="$(git rev-parse --short HEAD)"
        branch="$(git rev-parse --abbrev-ref HEAD)"
        log_info "当前版本: $branch @ $hash"
    fi
}

# ---------- 等待就绪 ----------
wait_for_ready() {
    log_info "等待服务启动..."
    local max_wait=300
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if curl -sf "http://127.0.0.1:${PORT_USER}/api/.well-known/endpoints" >/dev/null 2>&1; then
            log_success "服务已就绪!"
            return 0
        fi
        sleep 10
        waited=$((waited + 10))
        echo -n "."
    done
    echo ""
    log_warn "等待超时，服务可能还在启动中，请稍后再试"
    return 1
}

# ---------- 打印访问信息 ----------
print_access_info() {
    local ip
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP')"

    echo ""
    echo "=============================================="
    echo -e "  ${GREEN}Logto 源码构建部署成功!${NC}"
    echo "=============================================="
    echo ""
    echo "  用户端:  http://${ip}:${PORT_USER}"
    echo "  管理端:  http://${ip}:${PORT_ADMIN}"
    echo ""
    echo "  部署目录: $DEPLOY_DIR"
    echo "  源码目录: $SRC_DIR"
    echo "  配置文件: $ENV_FILE"
    echo "  日志文件: $DEPLOY_LOG"
    echo ""
    echo "  常用命令:"
    echo "    ./deploy-from-source.sh status    # 查看状态"
    echo "    ./deploy-from-source.sh logs      # 查看日志"
    echo "    ./deploy-from-source.sh restart   # 重启服务"
    echo "    ./deploy-from-source.sh update    # 拉取更新并重新构建"
    echo "    ./deploy-from-source.sh rebuild   # 强制重新构建"
    echo "    ./deploy-from-source.sh stop      # 停止服务"
    echo ""
    echo "  更新代码:"
    echo "    1. 修改你的 GitHub 仓库代码"
    echo "    2. 提交并推送到 $GIT_BRANCH 分支"
    echo "    3. 在服务器上运行: ./deploy-from-source.sh update"
    echo ""
    echo "=============================================="
}

# ---------- 主部署流程 ----------
deploy() {
    log_info "开始从源码构建部署 Logto..."
    echo ""

    check_environment
    prepare_deploy_dir
    load_env
    fetch_source || true
    build_image
    generate_compose_file
    generate_env_file
    load_env
    start_services
    wait_for_ready || true
    print_access_info
}

# ---------- 更新流程 ----------
update_deploy() {
    log_info "更新 Logto (拉取代码 + 重新构建 + 部署)..."
    echo ""

    check_environment
    load_env

    if fetch_source; then
        build_image
        cd "$DEPLOY_DIR"
        docker compose up -d --force-recreate
        wait_for_ready || true
        log_success "更新完成!"
    else
        log_info "代码没有更新，跳过构建"
    fi
}

# ---------- 强制重建 ----------
rebuild() {
    log_warn "即将强制重新构建镜像（不使用缓存）"
    read -rp "确认继续? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "已取消"
        return 0
    fi

    BUILD_NO_CACHE=1
    check_environment
    load_env

    if [ ! -d "$SRC_DIR/.git" ]; then
        fetch_source
    fi

    build_image
    cd "$DEPLOY_DIR"
    docker compose up -d --force-recreate
    wait_for_ready || true
    log_success "重新构建完成!"
}

# ---------- 卸载 ----------
down_services() {
    log_warn "即将停止并移除所有容器（数据保留在 data 目录，源码保留在 src 目录）"
    read -rp "确认继续? [y/N] " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        cd "$DEPLOY_DIR"
        docker compose down
        log_success "服务已停止并移除"
    else
        log_info "已取消"
    fi
}

# ---------- 主入口 ----------
main() {
    init_logging

    local action="${1:-deploy}"

    case "$action" in
        deploy|up|install)
            deploy
            ;;
        start)
            load_env
            start_services
            ;;
        stop)
            load_env
            stop_services
            ;;
        restart)
            load_env
            restart_services
            ;;
        logs)
            shift
            load_env
            show_logs "$@"
            ;;
        status|ps)
            load_env
            show_status
            ;;
        update|upgrade)
            update_deploy
            ;;
        rebuild)
            rebuild
            ;;
        down|uninstall)
            load_env
            down_services
            ;;
        help|-h|--help)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deploy    从源码构建并一键部署（默认）"
            echo "  start     启动服务"
            echo "  stop      停止服务"
            echo "  restart   重启服务"
            echo "  logs      查看日志"
            echo "  status    查看状态"
            echo "  update    拉取最新代码并重新构建部署"
            echo "  rebuild   强制重新构建镜像（无缓存）"
            echo "  down      停止并移除容器"
            echo "  help      显示帮助"
            echo ""
            echo "环境变量:"
            echo "  DEPLOY_DIR       部署目录 (默认: \$HOME/logto-source)"
            echo "  GIT_REPO         源码仓库地址"
            echo "  GIT_BRANCH       源码分支 (默认: master)"
            echo "  IMAGE_NAME       镜像名称 (默认: logto-custom)"
            echo "  IMAGE_TAG        镜像标签 (默认: latest)"
            echo "  PORT_USER        用户端端口 (默认: 3001)"
            echo "  PORT_ADMIN       管理端端口 (默认: 3002)"
            echo "  ENDPOINT         用户端域名"
            echo "  ADMIN_ENDPOINT   管理端域名"
            echo "  BUILD_NO_CACHE   构建时不使用缓存 (0/1)"
            ;;
        *)
            log_error "未知命令: $action"
            echo "使用 $0 help 查看帮助"
            exit 1
            ;;
    esac
}

main "$@"
