#!/bin/bash
# 通过 HTTP 代理 CONNECT 隧道连接到腾讯云服务器
PROXY_IP="127.0.0.1"
PROXY_PORT="18080"

sshpass -p 'Sch13255884503' ssh -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -o ProxyCommand="socat - PROXY:${PROXY_IP}:%h:%p,proxyport=${PROXY_PORT}" \
  ubuntu@1.14.125.204
