#!/bin/bash
# 通过 HTTP 代理隧道 SCP 上传文件
# 用法: ./scp_proxy.sh 本地文件 服务器目标路径
set -e
LOCAL_FILE="$1"
REMOTE_PATH="$2"

expect <<EOF
set timeout 300
spawn scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand=/workspace/proxy_cmd.sh\ %h\ %p -o PreferredAuthentications=password -o PubkeyAuthentication=no $LOCAL_FILE ubuntu@1.14.125.204:$REMOTE_PATH
expect {
    "password:" {
        send "Sch13255884503\r"
        exp_continue
    }
    "Permission denied" {
        puts "ERROR: 认证失败"
        exit 1
    }
    eof
}
EOF
