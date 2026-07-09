#!/usr/bin/env python3
"""通过代理隧道 SSH 到#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script],#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found, trying alternative...")
    # Alternative: use pexpect
    try:
        import pexpect
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found, trying alternative...")
    # Alternative: use pexpect
    try:
        import pexpect
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand="socat - PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT}" -o PreferredAuthentications=password -o PubkeyAuthentication#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found, trying alternative...")
    # Alternative: use pexpect
    try:
        import pexpect
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand="socat - PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT}" -o PreferredAuthentications=password -o PubkeyAuthentication=no {USER}@{HOST}')
        child.expect("password:")
        child.sendline(PASS)
        child.expect("$ ")
        child.sendline("cd#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found, trying alternative...")
    # Alternative: use pexpect
    try:
        import pexpect
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand="socat - PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT}" -o PreferredAuthentications=password -o PubkeyAuthentication=no {USER}@{HOST}')
        child.expect("password:")
        child.sendline(PASS)
        child.expect("$ ")
        child.sendline("cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1")
        child.expect("$ ", timeout=#!/usr/bin/env python3
"""通过代理隧道 SSH 到服务器，设置文件下载服务"""
import subprocess
import sys

HOST = "1.14.125.204"
PORT = 22
USER = "ubuntu"
PASS = "Sch13255884503"
PROXY_PORT = 18080

expect_script = f"""
set timeout 300
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \\
    -o ProxyCommand=socat\\ -\\ PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT} \\
    -o PreferredAuthentications=password -o PubkeyAuthentication=no \\
    {USER}@{HOST}
expect "password:"
send "{PASS}\\r"
expect "$ "
send "cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1\\r"
expect "$ "
send "cd logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --exclude=.cache --exclude='dream-os-next/node_modules' --exclude='dream-os-next/dist' dream-os/ 2>&1 && ls -lh /tmp/dream-os-termux.tar.gz\\r"
expect "$ "
send "cd /tmp && python3 -m http.server 8080 &\\r"
expect "$ "
send "echo 'DOWNLOAD_SERVER_READY'\\r"
expect "$ "
send "exit\\r"
expect eof
"""

try:
    subprocess.run(["expect", "-c", expect_script], timeout=120)
    print("Server setup complete!")
except subprocess.TimeoutExpired:
    print("Timeout waiting for server")
except FileNotFoundError:
    print("expect not found, trying alternative...")
    # Alternative: use pexpect
    try:
        import pexpect
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand="socat - PROXY:127.0.0.1:%h:%p,proxyport={PROXY_PORT}" -o PreferredAuthentications=password -o PubkeyAuthentication=no {USER}@{HOST}')
        child.expect("password:")
        child.sendline(PASS)
        child.expect("$ ")
        child.sendline("cd /tmp && git clone --depth 1 https://github.com/1535273240sch-droid/logto.git 2>&1")
        child.expect("$ ", timeout=60)
        child.sendline("cd /tmp/logto && tar czf /tmp/dream-os-termux.tar.gz --exclude=node_modules --exclude=.git --exclude=.npm --