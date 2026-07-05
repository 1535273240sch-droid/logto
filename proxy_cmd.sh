#!/bin/bash
# HTTP CONNECT 代理隧道 - 作为 ssh/scp 的 ProxyCommand
# 用法: ProxyCommand /workspace/proxy_cmd.sh %h %p
exec socat - "PROXY:127.0.0.1:$1:$2,proxyport=18080"
