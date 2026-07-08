"""MCP Streamable HTTP — 标准 JSON-RPC 协议，兼容 RikkaHub 等 MCP 客户端"""
import json
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from dotenv import load_dotenv
load_dotenv("/app/.env")
from ...core.mcp_manager import get_mcp_tools, execute_mcp_tool

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

MCP_API_TOKEN = os.environ.get("MCP_API_TOKEN", "CHANGE_ME")
_server_info = {"name": "DreamOS-Filesystem", "version": "1.0.0"}


async def verify_token(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if auth[len("Bearer "):] != MCP_API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Bearer token")


@router.post("")
@router.post("/")
async def mcp_jsonrpc(request: Request, _: None = Depends(verify_token)):
    """标准 MCP JSON-RPC 入口，RikkaHub 选「Streamable HTTP」填此 URL"""
    body = await request.json()
    method = body.get("method", "")
    req_id = body.get("id")
    # JSON-RPC 通知：id 为 null 时不回复
    if req_id is None:
        from fastapi.responses import Response
        return Response(status_code=204)

    try:
        if method == "initialize":
            return _rpc_ok(req_id, {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": _server_info,
            })
        elif method == "notifications/initialized":
            return _rpc_ok(req_id, {})
        elif method == "tools/list":
            tools = []
            for t in get_mcp_tools():
                tools.append({
                    "name": t.name,
                    "description": getattr(t, "description", ""),
                    "inputSchema": getattr(t, "inputSchema", {}),
                })
            return _rpc_ok(req_id, {"tools": tools})
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result_text = await execute_mcp_tool(name, arguments)
            return _rpc_ok(req_id, {
                "content": [{"type": "text", "text": result_text}]
            })
        elif method == "ping":
            return _rpc_ok(req_id, {})
        else:
            return _rpc_err(req_id, -32601, f"Method not found: {method}")
    except Exception as e:
        return _rpc_err(req_id, -32603, str(e))


def _rpc_ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
