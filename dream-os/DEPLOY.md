# 梦幻 · Dream — 部署指南

> 一份详细的部署文档，覆盖云服务器、本地 Linux、Termux 等平台。

---

## 目录

1. [环境要求](#1-环境要求)
2. [项目结构说明](#2-项目结构说明)
3. [配置说明](#3-配置说明)
4. [云服务器部署（Docker 方式）](#4-云服务器部署docker-方式)
5. [本地 Linux 部署（无 Docker）](#5-本地-linux-部署无-docker)
6. [Termux（Android 手机）部署](#6-termuxandroid-手机部署)
7. [更新升级](#7-更新升级)
8. [常见问题排查](#8-常见问题排查)

---

## 1. 环境要求

### 通用要求
- **Git**: 拉取代码
- **网络**: 需要能访问 GitHub 和 AI API
- **存储**: 至少 500MB 可用空间

### 各平台具体要求

| 平台 | 必须 | 可选 |
|------|------|------|
| 云服务器 | Docker + Docker Compose | Node.js 18+（用于前端构建） |
| 本地 Linux | Python 3.10+, Node.js 18+ | Docker |
| Termux | Python 3.10+, Node.js 18+ | Termux:Boot（开机自启） |

---

## 2. 项目结构说明

```
dream-os/
├── deploy.sh              # 云服务器 Docker 部署脚本
├── local-deploy.sh        # 本地 Linux 部署脚本（无 Docker）
├── termux-deploy.sh       # Termux 部署脚本
├── .env.example           # 环境变量模板
├── docker-compose.yml     # Docker Compose 配置
│
├── backend/               # Python FastAPI 后端
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py        # 入口文件
│       ├── config.py      # 配置加载
│       ├── core/          # 核心逻辑
│       ├── api/           # API 路由
│       ├── models/        # 数据模型
│       └── tools/         # 工具模块
│
├── dream-os-next/         # 前端（TypeScript + React + Vite）
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/               # 源码
│   ├── components/        # UI 组件
│   ├── core/              # 前端状态管理
│   └── dist/              # 构建产物（部署后生成）
│
├── core/                  # 核心模块（Python）
├── services/              # 微服务模块（Python）
├── docs/                  # 架构文档
└── docker/                # Docker 辅助配置
    └── nginx/
        └── default.conf   # Nginx 配置（用于 Docker 部署）
```

---

## 3. 配置说明

### 3.1 环境变量

核心配置在 `.env` 文件中，复制自 `.env.example`：

```bash
# === AI 模型（必填） ===
# API 地址（默认 OpenAI，可改为其他兼容接口）
AI_PROVIDER_BASE_URL=https://api.openai.com/v1
# API Key（必填！从 AI 服务商获取）
AI_PROVIDER_API_KEY=sk-your-api-key-here
# 模型名称
AI_PROVIDER_MODEL=gpt-4o

# === 数据库（可改，默认即可） ===
DB_USER=dream
DB_PASSWORD=dream123
DB_NAME=dreamos

# === 安全配置 ===
MAX_LOOP_ITERATIONS=15        # AI 最大循环次数
SANDBOX_TIMEOUT_SECONDS=30    # 沙箱超时时间
TTYD_PASSWORD=your-ttyd-password  # 终端密码
```

### 3.2 获取 API Key

| 服务商 | 获取地址 | 备注 |
|--------|----------|------|
| OpenAI | https://platform.openai.com/api-keys | 需要海外信用卡 |
| DeepSeek | https://platform.deepseek.com/api_keys | 国内可用，价格低 |
| 通义千问 | https://dashscope.aliyun.com/ | 阿里云，国内可用 |
| Claude | https://console.anthropic.com/ | 需要海外信用卡 |

修改 `.env` 中的 `AI_PROVIDER_BASE_URL` 和 `AI_PROVIDER_API_KEY` 即可切换。

---

## 4. 云服务器部署（Docker 方式）

> 适用于腾讯云、阿里云、AWS 等云服务器。
> 推荐系统：Ubuntu 20.04+ / Debian 11+ / CentOS 8+

### 4.1 一键部署（推荐）

**步骤 1：连接服务器**

```bash
ssh ubuntu@你的服务器IP
```

**步骤 2：运行部署脚本**

```bash
curl -fsSL https://raw.githubusercontent.com/1535273240sch-droid/logto/master/dream-os/deploy.sh | bash
```

脚本会自动：
- 检查并安装 Docker
- 检查 Docker Compose
- 克隆代码到 `/dream-os`
- 安装 Node.js 并构建前端
- 自动创建 `.env`（第一次运行后需编辑）

**步骤 3：编辑 API Key**

```bash
vim /dream-os/.env
```

将 `AI_PROVIDER_API_KEY=sk-your-api-key-here` 改为你的真实 Key。

**步骤 4：再次运行完成部署**

```bash
bash /dream-os/deploy.sh
```

### 4.2 手动分步部署

如果想自己控制每一步，可以手动操作：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 重新登录后生效

# 2. 安装 Docker Compose 插件
sudo apt-get install -y docker-compose-plugin

# 3. 克隆代码
git clone --depth 1 https://github.com/1535273240sch-droid/logto.git /tmp/logto
sudo cp -r /tmp/logto/dream-os /dream-os
cd /dream-os

# 4. 安装 Node.js 并构建前端
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
sudo apt-get install -y nodejs
npm install -g pnpm
cd /dream-os/dream-os-next
pnpm install
pnpm build
cd /dream-os

# 5. 配置环境变量
cp .env.example .env
vim .env   # 填入 API Key

# 6. 创建 Docker 网络（首次）
docker network create dream-os_default

# 7. 构建并启动
docker compose build --parallel
docker compose up -d

# 8. 验证
curl http://localhost:8000/api/health
```

### 4.3 各云服务商安全组/防火墙配置

#### 腾讯云
1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 **云服务器** → **实例** → 找到你的实例
3. 点击 **更多** → **安全组** → **配置规则**
4. 添加入站规则：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 3000 | 0.0.0.0/0 | 前端访问 |
| TCP | 22 | 你的IP | SSH 管理（建议限制来源IP） |

#### 阿里云
1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 进入 **网络与安全** → **安全组**
3. 找到实例所在安全组 → **配置规则** → **入方向**
4. 添加入站规则同上。

#### AWS
1. 登录 [AWS Console](https://console.aws.amazon.com/)
2. 进入 **EC2** → **安全组**
3. 找到实例的安全组 → **编辑入站规则**
4. 添加 HTTP (3000) 和 SSH (22) 规则。

### 4.4 访问服务

部署完成后：
- **前端**: `http://你的服务器IP:3000`
- **后端 API**: `http://你的服务器IP:8000/api`

### 4.5 常用 Docker 命令

```bash
# 查看日志
docker compose logs -f backend

# 查看运行状态
docker compose ps

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 重新构建并启动（代码更新后）
docker compose build --parallel
docker compose up -d
```

---

## 5. 本地 Linux 部署（无 Docker）

> 适用于 Ubuntu、Debian、CentOS、macOS 等系统。
> 如果你没有安装 Docker，或者不想用 Docker，可以用此方式。

### 5.1 前置检查

确保系统已安装：

```bash
# 检查 Python
python3 --version   # 需要 3.10+

# 检查 Node.js
node --version      # 需要 18+

# 检查 pnpm
pnpm --version      # 没有的话: npm install -g pnpm

# 检查 Git
git --version
```

### 5.2 一键部署

```bash
# 克隆代码
git clone --depth 1 https://github.com/1535273240sch-droid/logto.git /tmp/logto
cp -r /tmp/logto/dream-os ~/dream-os
cd ~/dream-os

# 运行部署脚本
bash local-deploy.sh
```

第一次运行会自动创建 `.env` 文件，编辑后再次运行：

```bash
vim ~/dream-os/.env   # 填入 API Key
bash local-deploy.sh
```

### 5.3 手动部署

```bash
# 1. 克隆代码
git clone --depth 1 https://github.com/1535273240sch-droid/logto.git /tmp/logto
cp -r /tmp/logto/dream-os ~/dream-os
cd ~/dream-os

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填入 API Key

# 3. 安装后端依赖
cd ~/dream-os/backend
pip3 install -r requirements.txt

# 4. 构建前端
cd ~/dream-os/dream-os-next
pnpm install
pnpm build

# 5. 启动服务
export PYTHONPATH="$HOME/dream-os/backend:$HOME/dream-os/core:$HOME/dream-os/services"

# 启动后端（后台运行）
cd ~/dream-os/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 启动前端（后台运行）
cd ~/dream-os/dream-os-next
python3 -m http.server 3000 --directory dist &

echo "前端: http://localhost:3000"
echo "后端: http://localhost:8000/api"
```

### 5.4 停止服务

```bash
# 查看后端和前端进程
ps aux | grep -E 'uvicorn|http.server.*3000'

# 停止（替换为实际的 PID）
kill <后端PID> <前端PID>
```

### 5.5 设置开机自启（systemd）

创建 systemd 服务文件：

```bash
sudo tee /etc/systemd/system/dream-os.service << 'EOF'
[Unit]
Description=Dream OS
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/dream-os
Environment=PYTHONPATH=/home/你的用户名/dream-os/backend:/home/你的用户名/dream-os/core:/home/你的用户名/dream-os/services
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
WorkingDirectory=/home/你的用户名/dream-os/backend
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable dream-os
sudo systemctl start dream-os
```

---

## 6. Termux（Android 手机）部署

### 6.1 安装 Termux

1. 从 [F-Droid](https://f-droid.org/packages/com.termux/) 下载安装 Termux（**推荐**，比 Google Play 版本更新）
2. 或者从 GitHub Releases 下载: https://github.com/termux/termux-app/releases

> 注意：**不要从 Google Play 安装 Termux**，Play 版已停止更新。

### 6.2 授予存储权限

打开 Termux，运行：

```bash
termux-setup-storage
```

手机会弹出权限请求，点击 **允许**。

### 6.3 一键部署（推荐）

在 Termux 中依次运行：

```bash
# 安装必要工具
pkg update -y
pkg install -y curl git

# 拉取部署脚本
curl -fsSL https://raw.githubusercontent.com/1535273240sch-droid/logto/master/dream-os/termux-deploy.sh > termux-deploy.sh
bash termux-deploy.sh
```

第一次运行会自动安装依赖并拉取代码，然后提示你编辑 `.env` 文件。

### 6.4 编辑 API Key

```bash
# 使用 nano 编辑（如果提示安装，按 y 确认）
nano ~/dream-os/.env
```

找到 `AI_PROVIDER_API_KEY=sk-your-api-key-here`，改为你的真实 Key：
```
AI_PROVIDER_API_KEY=sk-xxxxx
```

按 `Ctrl+X`，然后按 `Y`，再按 `Enter` 保存退出。

### 6.5 完成部署

```bash
bash termux-deploy.sh
```

### 6.6 访问服务

在 Termux 部署完成后，在手机浏览器中访问：

- **前端**: http://localhost:3000
- **后端 API**: http://localhost:8000/api

> 如果想在电脑上访问手机上的服务，需要手机和电脑在同一局域网，然后使用手机的局域网 IP：
> 1. 在 Termux 中运行 `ifconfig` 查看 IP（如 `192.168.1.xxx`）
> 2. 在电脑浏览器访问 `http://192.168.1.xxx:3000`

### 6.7 保持后台运行

Termux 默认在后台会被系统杀死。以下是几种解决方案：

#### 方法一：Termux:WakeLock（防止休眠）

```bash
pkg install -y termux-api
termux-wake-lock
```

#### 方法二：Termux:Boot（开机自启）

1. 从 F-Droid 安装 [Termux:Boot](https://f-droid.org/packages/com.termux.boot/)
2. 创建启动脚本：

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-dreamos.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# 等待网络就绪
sleep 10
# 启动 dream-os
cd ~/dream-os
export PYTHONPATH="$HOME/dream-os/backend:$HOME/dream-os/core:$HOME/dream-os/services"
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd ~/dream-os/dream-os-next
python3 -m http.server 3000 --directory dist &
EOF
chmod +x ~/.termux/boot/start-dreamos.sh
```

#### 方法三：使用 tmux（防止 SSH 断开）

```bash
pkg install -y tmux
tmux new -s dreamos
# 在 tmux 中运行部署脚本
bash termux-deploy.sh
# 按 Ctrl+B 然后按 D 分离会话
# 重新连接: tmux attach -t dreamos
```

### 6.8 停止服务

```bash
# 杀掉进程
pkill -f "uvicorn app.main:app"
pkill -f "http.server 3000"

# 或直接重启 Termux（从通知栏退出）
```

### 6.9 网络配置（手机热点）

> 适用于：想通过电脑或其他设备访问手机上的 dream-os。

**第 1 步：手机开启热点**
- 在手机设置中开启 **个人热点**

**第 2 步：查看手机在热点网络中的 IP**
```bash
# 在 Termux 中运行
ifconfig
# 找到 wlan0 或类似接口，查看 inet 地址
# 通常热点 IP 是 192.168.43.1 或 192.168.0.1
```

**第 3 步：电脑连接手机热点**
- 电脑连接手机 Wi-Fi 热点
- 浏览器访问 `http://手机热点IP:3000`
- 如 `http://192.168.43.1:3000`

**确保后端监听 0.0.0.0**（脚本已默认设置，无需修改）。

---

## 7. 更新升级

### 7.1 云服务器（Docker 方式）

```bash
bash /dream-os/deploy.sh
```

脚本会自动拉取最新代码、重新构建前端和 Docker 镜像。

### 7.2 本地 Linux / Termux

```bash
bash ~/dream-os/termux-deploy.sh
# 或
bash ~/dream-os/local-deploy.sh
```

### 7.3 手动更新

```bash
cd ~/dream-os
git fetch origin master
git reset --hard origin/master
# 重新构建前端
cd dream-os-next
pnpm install
pnpm build
# 重启后端
pkill -f "uvicorn app.main:app"
cd ~/dream-os/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

---

## 8. 常见问题排查

### 8.1 端口被占用

```bash
# 查看端口占用
lsof -i :3000
lsof -i :8000

# 杀掉占用进程
kill -9 <PID>
```

### 8.2 Python 模块找不到

```bash
# 确保设置了 PYTHONPATH
export PYTHONPATH="/path/to/dream-os/backend:/path/to/dream-os/core:/path/to/dream-os/services:$PYTHONPATH"
```

### 8.3 前端构建失败

```bash
# 清理缓存重新安装
cd ~/dream-os/dream-os-next
rm -rf node_modules dist
pnpm install
pnpm build
```

### 8.4 Termux 中 pip 安装失败

```bash
# 更新 pip
pip install --upgrade pip

# 如果 still 失败，尝试使用 pkg 安装 Python 包
pkg install -y python-numpy  # 示例

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 8.5 Termux 连接被拒绝

```bash
# 检查服务是否在运行
ps aux | grep -E 'uvicorn|http.server'

# 检查端口监听
ss -tlnp | grep -E '3000|8000'

# 如果没运行，重新执行部署脚本
```

### 8.6 API 连接错误

```bash
# 检查 .env 配置
cat ~/dream-os/.env | grep AI_PROVIDER

# 确保 API Key 正确
# 确保 AI_PROVIDER_BASE_URL 正确（如使用 OpenAI 则不变）
# 测试 API 连通性
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer 你的API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'
```

### 8.7 数据库问题

Dream OS 默认使用 SQLite（不需要额外配置）。如果需要切换 PostgreSQL：

```bash
# 安装 PostgreSQL
# 修改 .env 中的数据库配置
DB_USER=dream
DB_PASSWORD=dream123
DB_NAME=dreamos
# 添加 DB_HOST=localhost
# 添加 DB_PORT=5432
```

---

## 附录

### 各部署方式对比

| 特性 | 云服务器 Docker | 本地 Linux | Termux |
|------|----------------|------------|--------|
| 部署难度 | 中等 | 简单 | 简单 |
| 性能 | 最高 | 高 | 中等 |
| 可用性 | 24小时 | 取决于电脑开机 | 取决于手机后台 |
| 公网访问 | 支持 | 需内网穿透 | 需内网穿透 |
| 维护成本 | 低 | 低 | 中（后台保活） |
| 适合场景 | 生产环境 | 开发测试 | 个人体验、移动开发 |

### 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | 前端（Nginx/Python HTTP） | 浏览器访问 |
| 8000 | 后端（FastAPI/Uvicorn） | API 接口 |

### 相关链接

- GitHub 仓库: https://github.com/1535273240sch-droid/logto
- 部署脚本: https://github.com/1535273240sch-droid/logto/tree/master/dream-os
- Termux 官网: https://termux.com/
- Docker 安装: https://docs.docker.com/engine/install/