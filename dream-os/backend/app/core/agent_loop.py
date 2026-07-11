"""Agent Loop — AI Agent 执行器"""
import json, asyncio, uuid, logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass, field
from ..config import get_settings
from ..core.ai_provider import get_ai_client
from ..tools import ToolManager, ShellTool, FileTool, HttpTool
from ..tools.weather import WeatherTool
from ..tools.stock import StockTool
from ..core.response_cache import get_response_cache
from ..tools.image import ImageTool
logger = logging.getLogger("dream-os.agent_loop")

# 任务确认信号（用于 task.py 的 confirm 端点）
_pending_confirmations: dict[str, asyncio.Event] = {}
_confirm_results: dict[str, bool] = {}


def signal_confirmation(task_id: str, confirmed: bool):
    """发送确认信号给正在等待的 Agent"""
    _confirm_results[task_id] = confirmed
    if task_id in _pending_confirmations:
        _pending_confirmations[task_id].set()
CHAT_SYSTEM_PROMPT = """你是 Dream OS 的 AI 助手。
## 可用工具
- stock_query: 查询股票、黄金、白银、加密货币实时价格
  * 黄金: stock:黄金
  * 白银: stock:白银
  * 股票: stock:00700.HK / stock:AAPL / stock:600519.SH
  * 加密货币: crypto:bitcoin
- weather_query: 查询天气（weather:城市名）
- http_fetch: 联网查询信息
- shell_exec: 执行 Linux 命令
- image_generate: 生成图片（image:描述词），支持"赛博朋克/水墨/油画/水彩/素描/像素/动漫/写实/3D/卡通"风格，在描述词中加入风格关键词即可
## 规则
1. 常识/百科问题直接回答，不调用工具
2. 实时信息（天气、股价、金价、新闻）调用工具查询
3. 每次只调用一个工具
4. 简洁、自然，不暴露工具调用细节
5. 工具失败时告知用户原因，不要重复调用同一工具
6. 生成图片后，把图片 URL 放在回复末尾，格式为：![图片](URL)"""
MAX_LOOP_ITERATIONS = 5
@dataclass
class AgentStep:
    agent: str; description: str
    status: str = "pending"; result: Any = None; error: str = ""
    started_at: Optional[str] = None; completed_at: Optional[str] = None
# 连接池预热
async def prewarm_ai_client():
    """服务启动时预建 AI 客户端连接"""
    try:
        await get_ai_client()
        logger.info("AI client pre-warmed")
    except Exception as e:
        logger.warning(f"AI client pre-warm failed: {e}")

class AgentLoop:
    def __init__(self, db=None):
        self._steps: List[AgentStep] = []
        self._loop_id = str(uuid.uuid4())[:8]
        self._tool_manager: Optional[ToolManager] = None
        self._db = db
    def _init_tools(self):
        if self._tool_manager is not None: return
        self._tool_manager = ToolManager()
        self._tool_manager.register(ShellTool())
        self._tool_manager.register(FileTool())
        self._tool_manager.register(HttpTool())
        self._tool_manager.register(WeatherTool())
        self._tool_manager.register(StockTool())
        self._tool_manager.register(ImageTool())
    def _sse(self, event_type: str, data: dict) -> str:
        payload = json.dumps(data, ensure_ascii=False)
        return f"data: {payload}\n\n"
    async def run_chat(self, message: str, context: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        self._init_tools()
        tool_schemas = self._tool_manager.list_schemas() if self._tool_manager else []
        try:
            client, model = await get_ai_client(self._db, tier="deep")
        except Exception as e:
            yield self._sse("content", {"type": "content", "content": f"AI 服务连接失败: {str(e)[:200]}"})
            yield self._sse("done", {"type": "done"})
            return
        messages: List[Dict] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        # 语义缓存检查
        cache = get_response_cache()
        cached = cache.get(message)
        if cached:
            yield self._sse("content", {"type": "content", "content": cached})
            yield self._sse("done", {"type": "done"})
            return

        called_tools = set()
        for iteration in range(1, MAX_LOOP_ITERATIONS + 1):
            try:
                kwargs = dict(model=model, messages=messages, temperature=0.7, max_tokens=1024)
                if tool_schemas:
                    kwargs["tools"] = tool_schemas
                    kwargs["tool_choice"] = "auto"
                response = await client.chat.completions.create(**kwargs)
                msg = response.choices[0].message
                if not msg.tool_calls:
                    content = msg.content or ""
                    cache.set(message, content)
                    yield self._sse("content", {"type": "content", "content": content})
                    yield self._sse("done", {"type": "done"})
                    return
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    if tool_name in called_tools:
                        yield self._sse("content", {"type": "content", "content": "该工具已执行过，基于已有结果为您回答。"})
                        yield self._sse("done", {"type": "done"})
                        return
                    called_tools.add(tool_name)
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {"command": tc.function.arguments}
                    command = arguments.get("command", "")
                    yield self._sse("tool_start", {"type": "tool_start", "tool": tool_name, "description": command[:100]})
                    try:
                        tool = self._tool_manager.get(tool_name) if self._tool_manager else None
                        if not tool:
                            tool_result = {"success": False, "output": f"工具 '{tool_name}' 不可用"}
                        else:
                            result = await tool.execute(command, timeout=30)
                            tool_result = {"success": result.success, "output": (result.stdout or result.stderr or "")[:3000]}
                    except Exception as e:
                        tool_result = {"success": False, "output": f"工具执行异常: {str(e)[:200]}"}
                    yield self._sse("tool_result", {"type": "tool_result", "tool": tool_name, "success": tool_result["success"], "output": tool_result["output"][:300]})
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}]})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_result["output"][:4000]})
            except Exception as e:
                logger.error(f"Chat loop iteration {iteration} failed: {e}", exc_info=True)
                yield self._sse("content", {"type": "content", "content": f"抱歉，处理请求时出错: {str(e)[:200]}"})
                yield self._sse("done", {"type": "done"})
                return
        yield self._sse("content", {"type": "content", "content": "处理超时，请简化您的请求后重试。"})
        yield self._sse("done", {"type": "done"})
    async def run_dev(self, task: str, context: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        try:
            from ..core.v3 import AutoLoop
            from ..tools import ToolManager as TM, ShellTool as ST, FileTool as FT, HttpTool as HT
            tool_manager = TM(); tool_manager.register(ST()); tool_manager.register(FT()); tool_manager.register(HT())
            auto_loop = AutoLoop(tool_manager)
            async def emit(event: dict): pass
            async for event in auto_loop.run(requirement=task, task_id=f"dev_{uuid.uuid4().hex[:8]}", emit=emit, max_iterations=3):
                yield self._sse(event.get("type", "unknown"), event)
        except ImportError as e:
            logger.warning(f"V3 not available: {e}")
            dev_pipeline = [("planner","规划"),("architect","架构"),("coder","编码"),("executor","构建"),("reviewer","审查"),("tester","测试"),("deployer","部署"),("reporter","报告")]
            yield self._sse("dev_start", {"type": "dev_start", "task": task, "agents": [{"role": n, "name": f"{n}（模拟）", "emoji": "🤖", "description": d} for n, d in dev_pipeline]})
            for n, d in dev_pipeline:
                yield self._sse("agent_start", {"type": "agent_start", "agent": n, "name": n, "task": d})
                yield self._sse("agent_complete", {"type": "agent_complete", "agent": n, "success": True})
            yield self._sse("dev_complete", {"type": "dev_complete", "success": True, "summary": "开发完成（模拟模式）"})
    async def run(self, task: str) -> str:
        return f"Task executed: {task[:100]}"
    def get_steps(self) -> List[AgentStep]:
        return self._steps
