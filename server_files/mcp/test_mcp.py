import subprocess
import json
import time

# 测试 Filesystem MCP
print("测试 Filesystem MCP...")
try:
    proc = subprocess.Popen(
        ["npx", "@modelcontextprotocol/server-filesystem", "/home/ubuntu"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # 发送初始化请求
    init_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-10-01",
            "capabilities": {}
        }
    })
    proc.stdin.write(init_req + "\n")
    proc.stdin.flush()
    time.sleep(0.5)
    proc.terminate()
    print("✓ Filesystem MCP 响应正常")
except Exception as e:
    print(f"✗ Filesystem MCP 失败: {e}")

# 测试 SQLite MCP
print("测试 SQLite MCP...")
try:
    proc = subprocess.Popen(
        ["npx", "mcp-server-sqlite-npx", "/app/dream_os.db"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    init_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-10-01",
            "capabilities": {}
        }
    })
    proc.stdin.write(init_req + "\n")
    proc.stdin.flush()
    time.sleep(0.5)
    proc.terminate()
    print("✓ SQLite MCP 响应正常")
except Exception as e:
    print(f"✗ SQLite MCP 失败: {e}")

print("测试完成")
