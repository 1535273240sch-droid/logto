"""
MCP Manager — 基于 Python mcp SDK 管理 Filesystem MCP Server
"""
import asyncio
import json
import logging
from typing import Optional
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

logger = logging.getLogger("dream-os.mcp")


class MCPManager:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._client_ctx = None
        self._tools: list = []
        self._read_task: Optional[asyncio.Task] = None

    async def start_filesystem(self, allowed_dir: str = "/app"):
        if not MCP_AVAILABLE:
            logger.warning("MCP package not installed, skipping filesystem MCP")
            return False
        server_params = StdioServerParameters(
            command="npx",
            args=["@modelcontextprotocol/server-filesystem", allowed_dir],
        )
        self._client_ctx = stdio_client(server_params)
        reader, writer = await self._client_ctx.__aenter__()
        self.session = await ClientSession(reader, writer).__aenter__()
        await self.session.initialize()
        tools_result = await self.session.list_tools()
        self._tools = list(tools_result.tools)
        logger.info(f"MCP Filesystem initialized, {len(self._tools)} tools loaded")
        return True

    def get_tools(self) -> list:
        return self._tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        result = await self.session.call_tool(name, arguments)
        parts = []
        if hasattr(result, 'content'):
            for c in result.content:
                if hasattr(c, 'text'):
                    parts.append(c.text)
                elif hasattr(c, 'data'):
                    parts.append(str(c.data))
                else:
                    parts.append(str(c))
        return "\n".join(parts)

    async def shutdown(self):
        if not MCP_AVAILABLE:
            return
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._client_ctx:
            await self._client_ctx.__aexit__(None, None, None)
        logger.info("MCP shutdown complete")


# 全局单例
_manager: Optional[MCPManager] = None


async def init_mcp():
    global _manager
    try:
        _manager = MCPManager()
        ok = await _manager.start_filesystem()
        if ok:
            tools = _manager.get_tools()
            tool_names = [t.name for t in tools]
            logger.info(f"MCP ready: {tool_names}")
        return ok
    except Exception as e:
        logger.error(f"MCP init failed: {e}")
        _manager = None
        return False


def get_mcp_tools() -> list:
    return _manager.get_tools() if _manager else []


async def execute_mcp_tool(name: str, arguments: dict) -> str:
    if not _manager:
        raise RuntimeError("MCP not initialized")
    return await _manager.call_tool(name, arguments)


async def shutdown_mcp():
    global _manager
    if _manager:
        await _manager.shutdown()
        _manager = None
