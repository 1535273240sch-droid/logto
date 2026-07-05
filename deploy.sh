#!/bin/bash
set -euo pipefail

# ============================================================
# Logto 一键部署脚本
# 支持：Docker Compose 部署、自动安装依赖、生产环境配置
# 用法：
#   ./deploy.sh              # 一键部署
#   ./deploy.sh start        # 启动服务
#   ./deploy.sh stop         # 停止服务
#   ./deploy.sh restart      # 重启服务
#   ./deploy.sh logs         # 查看日志
#   ./deploy.sh update       # 更新并重启
#   ./deploy.sh down         # 停止并移除容器
#   ./deploy.sh status       # 查看状态
# ============================================================

# ---------- 配置 ----------
PROJECT_NAME="logto"
DEPLOY_DIR="${DEPLOY_DIR:-$HOME/logto}"
LOG_DIR="$HOME/.local/var/log/logto"
DEPLOY_LOG="$LOG_DIR/deploy.log"
ENV_FILE="$DEPLOY_DIR/.env"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"

# 镜像配置
LOGTO_IMAGE="${LOGTO_IMAGE:-svhd/logto:latest}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:17-alpine}"

# 端口配置
PORT_USER="${PORT_USER:-3001}"
PORT_ADMIN="${PORT_ADMIN:-3002}"
PORT_POSTGRES="${PORT_POSTGRES:-5432}"

# 数据库配置
DB_USER="${DB_USER:-logto}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-logto}"

# Logto 配置
ENDPOINT="${ENDPOINT:-}"
ADMIN_ENDPOINT="${ADMIN_ENDPOINT:-}"
TRUST_PROXY_HEADER="${TRUST_PROXY_HEADER:-1}"

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------- 日志函数（必须返回0，避免被 set -e 中断） ----------
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

# ---------- 初始化日志目录 ----------
init_logging() {
    mkdir -p "$(dirname "$DEPLOY_LOG")" 2>/dev/null || true
    : > "$DEPLOY_LOG" 2>/dev/null || true
    return 0
}

# ---------- 检查并安装 Docker ----------
check_docker() {
    log_info "检查 Docker 环境..."

    if command_exists docker; then
        log_success "Docker 已安装: $(docker --version)"
    else
        log_warn "Docker 未安装，开始自动安装..."
        install_docker
    fi

    if docker compose version >/dev/null 2>&1; then
        log_success "Docker Compose 已安装: $(docker compose version --short)"
    else
        log_error "Docker Compose 不可用"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_warn "当前用户可能没有 Docker 权限，尝试使用 sudo..."
        if command_exists sudo && sudo docker info >/dev/null 2>&1; then
            alias docker='sudo docker'
            log_success "已切换为 sudo docker 模式"
        else
            log_error "无法访问 Docker 守护进程，请确保 Docker 已启动且当前用户有权限"
            exit 1
        fi
    fi
}

install_docker() {
    local os_type
    os_type="$(. /etc/os-release && echo "$ID")"

    case "$os_type" in
        ubuntu|debian)
            log_info "使用 apt 安装 Docker..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes 2>/dev/null || true
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update -qq
            sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
            ;;
        centos|rhel|rocky|almalinux)
            log_info "使用 yum/dnf 安装 Docker..."
            sudo yum install -y -q yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo systemctl enable --now docker
            ;;
        *)
            log_error "不支持的操作系统: $os_type，请手动安装 Docker"
            log_info "参考: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac

    log_success "Docker 安装完成"
}

# ---------- 创建部署目录 ----------
prepare_deploy_dir() {
    log_info "部署目录: $DEPLOY_DIR"
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
    image: ${LOGTO_IMAGE}
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

    # 自动生成数据库密码
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD="$(generate_password)"
        log_info "已自动生成数据库密码"
    fi

    cat > "$ENV_FILE" << EOF
# ============================================================
# Logto 部署配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

# 项目配置
PROJECT_NAME=${PROJECT_NAME}

# 镜像配置
LOGTO_IMAGE=${LOGTO_IMAGE}
POSTGRES_IMAGE=${POSTGRES_IMAGE}

# 端口配置
PORT_USER=${PORT_USER}
PORT_ADMIN=${PORT_ADMIN}
PORT_POSTGRES=${PORT_POSTGRES}

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

    # 提示需要修改的配置
    if [ -z "$ENDPOINT" ]; then
        log_warn "⚠️  未配置 ENDPOINT，首次访问后请在管理控制台中设置正确的域名"
    fi
}

# ---------- 加载 .env 文件 ----------
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
    log_info "日志文件: $DEPLOY_LOG"
}

# ---------- 更新服务 ----------
update_services() {
    log_info "更新 Logto 服务..."
    cd "$DEPLOY_DIR"
    docker compose pull
    docker compose up -d
    log_success "服务已更新并重启"
}

# ---------- 卸载服务 ----------
down_services() {
    log_warn "即将停止并移除所有容器（数据保留在 data 目录）"
    read -rp "确认继续? [y/N] " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        cd "$DEPLOY_DIR"
        docker compose down
        log_success "服务已停止并移除"
    else
        log_info "已取消"
    fi
}

# ---------- 等待服务就绪 ----------
wait_for_ready() {
    log_info "等待服务启动..."
    local max_wait=120
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if curl -sf "http://127.0.0.1:${PORT_USER}/api/.well-known/endpoints" >/dev/null 2>&1; then
            log_success "服务已就绪!"
            return 0
        fi
        sleep 5
        waited=$((waited + 5))
        echo -n "."
    done
    echo ""
    log_warn "等待超时，服务可能还在启动中，请稍后再试"
    return 1
}

# ---------- 打印访问信息 ----------
print_access_info() {
    echo ""
    echo "=============================================="
    echo -e "  ${GREEN}Logto 部署成功!${NC}"
    echo "=============================================="
    echo ""
    echo "  用户端:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP'):${PORT_USER}"
    echo "  管理端:  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_SERVER_IP'):${PORT_ADMIN}"
    echo ""
    echo "  部署目录: $DEPLOY_DIR"
    echo "  配置文件: $ENV_FILE"
    echo "  日志文件: $DEPLOY_LOG"
    echo ""
    echo "  常用命令:"
    echo "    ./deploy.sh status    # 查看状态"
    echo "    ./deploy.sh logs      # 查看日志"
    echo "    ./deploy.sh restart   # 重启服务"
    echo "    ./deploy.sh update    # 更新服务"
    echo "    ./deploy.sh stop      # 停止服务"
    echo ""
    echo "  ⚠️  首次使用请在管理控制台中:"
    echo "    1. 设置管理员账号"
    echo "    2. 配置正确的 ENDPOINT 和 ADMIN_ENDPOINT"
    echo "    3. 配置 HTTPS（推荐使用 Nginx 反向代理）"
    echo ""
    echo "=============================================="
}

# ---------- 主部署流程 ----------
deploy() {
    log_info "开始部署 Logto..."
    echo ""

    check_docker
    prepare_deploy_dir
    load_env
    generate_compose_file
    generate_env_file
    load_env  # 重新加载新生成的配置
    start_services
    wait_for_ready || true
    print_access_info
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
            load_env
            update_services
            ;;
        down|uninstall)
            load_env
            down_services
            ;;
        help|-h|--help)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deploy    一键部署（默认）"
            echo "  start     启动服务"
            echo "  stop      停止服务"
            echo "  restart   重启服务"
            echo "  logs      查看日志"
            echo "  status    查看状态"
            echo "  update    更新并重启"
            echo "  down      停止并移除容器"
            echo "  help      显示帮助"
            echo ""
            echo "环境变量:"
            echo "  DEPLOY_DIR   部署目录 (默认: \$HOME/logto)"
            echo "  PORT_USER    用户端端口 (默认: 3001)"
            echo "  PORT_ADMIN   管理端端口 (默认: 3002)"
            echo "  ENDPOINT     用户端域名"
            echo "  ADMIN_ENDPOINT  管理端域名"
            ;;
        *)
            log_error "未知命令: $action"
            echo "使用 $0 help 查看帮助"
            exit 1
            ;;
    esac
}

main "$@"
