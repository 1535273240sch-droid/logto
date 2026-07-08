#!/bin/bash
set -e

# 启动 Filesystem MCP (监听 /home/ubuntu 目录)
npx @modelcontextprotocol/server-filesystem /home/ubuntu &
FS_PID=$!

# 启动 SQLite MCP (连接 Dream OS 数据库)
npx mcp-server-sqlite-npx /app/dream_os.db &
SQLITE_PID=$!

echo "Filesystem MCP PID: $FS_PID (目录: /home/ubuntu)"
echo "SQLite MCP PID: $SQLITE_PID (数据库: /app/dream_os.db)"
echo "MCP 服务已启动, 按 Ctrl+C 停止"

# 等待子进程
wait $FS_PID $SQLITE_PID
