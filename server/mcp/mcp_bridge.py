"""
MCP Bridge — 管理 MCP Server 进程，通过 stdio/JSON-RPC 通信
供 Dream OS Agent Pipeline 调用
"""
import asyncio
import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger("dream-os.mcp_bridge")

MCP_SERVERS = {
    "filesystem": {
        "cmd": ["npx", "@modelcontextprotocol/server-filesystem", "/home/ubuntu"],
        "description": "安全的文件系统操作（读/写/搜索/列目录）",
        "work_dir": "/home/ubuntu"
    },
    "sqlite": {
        "cmd": ["npx", "mcp-server-sqlite-npx", "/dream-os/backend/dream_os.db"],
        "description": "SQLite 数据库查询（conversations/memories/tasks 等）",
        "work_dir": "/dream-os/backend"
    }
}

class MCPProcess:
    """单个 MCP Server 进程管理"""
    
    def __init__(self, name: str, cmd: list, work_dir: str):
        self.name = name
        self.cmd = cmd
        self.work_dir = work_dir
        self.proc: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()
        self._next_id = 1
    
    async def start(self):
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.work_dir
        )
        # 发送初始化
        resp = await self._request("initialize", {
            "protocolVersion": "2025-10-01",
            "capabilities": {}
        })
        logger.info(f"MCP [{self.name}] started: {resp.get('result', {}).get('serverInfo', '')}")
    
    async def _request(self, method: str, params: dict | None = None) -> dict:
        """发送 JSON-RPC 请求并等待响应"""
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError(f"MCP [{self.name}] 进程已退出")
        
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params or {}
        }
        self._next_id += 1
        
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        
        # 读取响应行
        line = self.proc.stdout.readline()
        return json.loads(line)
    
    async def list_tools(self) -> list[dict]:
        """列出可用工具"""
        resp = await self._request("tools/list")
        return resp.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用工具"""
        resp = await self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        return resp.get("result", {})
    
    async def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


class MCPBridge:
    """MCP 桥接管理器 — 管理所有 MCP Server"""
    
    def __init__(self):
        self.processes: dict[str, MCPProcess] = {}
        self._tools_cache: dict[str, list[dict]] = {}
    
    async def start_all(self):
        """启动所有 MCP Server"""
        for name, config in MCP_SERVERS.items():
            proc = MCPProcess(name, config["cmd"], config["work_dir"])
            try:
                await proc.start()
                self.processes[name] = proc
                # 缓存工具列表
                tools = await proc.list_tools()
                self._tools_cache[name] = tools
                tool_names = [t["name"] for t in tools]
                logger.info(f"MCP [{name}] tools: {tool_names}")
            except Exception as e:
                logger.error(f"MCP [{name}] 启动失败: {e}")
    
    async def stop_all(self):
        """停止所有 MCP Server"""
        for name, proc in self.processes.items():
            await proc.stop()
            logger.info(f"MCP [{name}] stopped")
        self.processes.clear()
    
    def get_all_tools(self) -> list[dict]:
        """获取所有工具列表"""
        tools = []
        for name, tool_list in self._tools_cache.items():
            for t in tool_list:
                tools.append({
                    "name": f"mcp_{name}_{t['name']}",
                    "description": f"[MCP:{name}] {t.get('description', '')}",
                    "inputSchema": t.get("inputSchema", {}),
                    "mcp_server": name,
                    "mcp_tool": t["name"]
                })
        return tools
    
    async def execute_tool(self, full_name: str, arguments: dict) -> dict:
        """执行 MCP 工具"""
        # full_name 格式: mcp_filesystem_read_file
        parts = full_name.split("_", 2)  # ["mcp", "filesystem", "read_file"]
        if len(parts) < 3:
            raise ValueError(f"Invalid tool name: {full_name}")
        
        server_name = parts[1]
        tool_name = parts[2]
        
        proc = self.processes.get(server_name)
        if not proc:
            raise ValueError(f"MCP server '{server_name}' not found")
        
        return await proc.call_tool(tool_name, arguments)


# 全局单例
bridge = MCPBridge()

async def test_bridge():
    """测试桥接器"""
    await bridge.start_all()
    
    print("\n=== 所有可用 MCP 工具 ===")
    for tool in bridge.get_all_tools():
        print(f"  {tool['name']}: {tool['description'][:80]}")
    
    # 测试 filesystem
    print("\n=== 测试 Filesystem: 列出 /home/ubuntu ===")
    try:
        result = await bridge.execute_tool("mcp_filesystem_list_directory", {"path": "/home/ubuntu"})
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    # 测试 SQLite
    print("\n=== 测试 SQLite: 列出表 ===")
    try:
        result = await bridge.execute_tool("mcp_sqlite_read_query", {"query": "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"})
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
    except Exception as e:
        print(f"Error: {e}")
    
    await bridge.stop_all()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_bridge())
