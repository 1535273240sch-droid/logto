"""HTTP Tool — 网络请求（使用 httpx 替代 curl 子进程，减少进程创建开销）"""
from .base import BaseTool, ToolResult


class HttpTool(BaseTool):
    """通过 httpx 发起 HTTP GET 请求获取网络数据"""

    name = "http_fetch"
    description = (
        "通过 curl 发起 HTTP GET 请求获取网络数据。"
        "可以用来查天气、新闻、API 等。"
        "命令格式: GET https://api.example.com/data"
    )

    async def execute(self, command: str, timeout: int = 15, **kwargs) -> ToolResult:
        import httpx

        cmd = command.strip()
        if cmd.upper().startswith("GET "):
            url = cmd[4:].strip()
        elif cmd.startswith("http://") or cmd.startswith("https://"):
            url = cmd
        else:
            return ToolResult(success=False, stderr=f"格式错误，请使用 GET <url> 格式", exit_code=1)

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                verify=False,
            ) as client:
                resp = await client.get(url)
                output = resp.text

            # 截断长输出
            if len(output) > 3000:
                output = output[:3000] + "\n...(已截断)"

            return ToolResult(
                success=resp.status_code < 400,
                stdout=output,
                stderr="" if resp.status_code < 400 else f"HTTP {resp.status_code}",
                exit_code=resp.status_code,
            )
        except httpx.TimeoutException:
            return ToolResult(success=False, stderr=f"请求超时 ({timeout}s)", exit_code=124)
        except Exception as e:
            return ToolResult(success=False, stderr=str(e), exit_code=1)

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "GET 请求的 URL。例如: GET https://api.example.com/weather",
                        }
                    },
                    "required": ["command"],
                },
            },
        }
