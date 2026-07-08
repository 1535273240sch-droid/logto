# 腾讯云服务器 SSH 连接指南

## 服务器信息
- **IP:** 1.14.125.204
- **用户:** ubuntu
- **密码:** Sch13255884503
- **系统:** Ubuntu 6.8.0-117-generic

## 本地环境 SSH 配置（~/.ssh/config）

将以下内容添加到本地机器的 ~/.ssh/config 中：

```ini
Host tencent
    HostName 1.14.125.204
    Port 22
    User ubuntu
    ProxyCommand socat - PROXY:127.0.0.1:%h:%p,proxyport=18080
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

## 连接方式

### 方式一：直接连接（密码）
```bash
ssh ubuntu@1.14.125.204
```

### 方式二：通过 HTTP 代理（socat + CONNECT 隧道）
```bash
ssh -o ProxyCommand="socat - PROXY:代理IP:%h:%p,proxyport=代理端口" ubuntu@1.14.125.204
```

### 方式三：通过 nc 代理
```bash
ssh -o ProxyCommand="nc -X connect -x 代理IP:代理端口 %h %p" ubuntu@1.14.125.204
```

## 前提条件
- 本地安装 socat: `apt install socat` 或 `brew install socat`
- 本地安装 sshpass（用于密码自动登录）: `apt install sshpass`
