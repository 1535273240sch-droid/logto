#!/usr/bin/expect -f
# 通过 HTTP CONNECT 代理隧道 SSH 到服务器 (支持多行命令)
# 用法: ./ssh_proxy.sh "远程命令"
set timeout 300
set cmd [lindex $argv 0]
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand=/workspace/proxy_cmd.sh\ %h\ %p -o PreferredAuthentications=password -o PubkeyAuthentication=no ubuntu@1.14.125.204 $cmd
expect {
    "password:" {
        send "Sch13255884503\r"
        exp_continue
    }
    "Permission denied" {
        puts "ERROR: 密码认证失败"
        exit 1
    }
    eof
}
