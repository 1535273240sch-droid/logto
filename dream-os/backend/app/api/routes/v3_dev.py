"""V3 自主开发 API V5.2 — SSE 流式接口 + 人机协作

POST /api/v3/dev/start          — 启动开发任务 (SSE)
GET  /api/v3/dev/tasks          — 任务列表
GET  /api/v3/dev/tasks/{id}     — 任务详情
GET  /api/v3/dev/tasks/{id}/files       — 文件列表
GET  /api/v3/dev/tasks/{id}/files/{p}   — 文件内容
GET  /api/v3/dev/tasks/{id}/status      — 进度
GET  /api/v3/dev/agents                 — Agent 列表
POST /api/v3/dev/tasks/{id}/pause|resume|stop
DELETE /api/v3/dev/tasks/{id}

V5.2 新增:
GET  /api/v3/dev/tasks/{id}/env         — 获取项目环境变量
POST /api/v3/dev/tasks/{id}/env         — 保存项目环境变量
POST /api/v3/dev/tasks/{id}/deploy      — 触发部署 (用户指定端口/方式)
POST /api/v3/dev/tasks/{id}/human-input — 接收用户输入 (人机协作关卡)
"""
import json, uuid, asyncio, logging, os, subprocess, sys
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models.dev_task import DevTask
from ...tools import ToolManager, ShellTool, FileTool, HttpTool
from ...core.v3 import AutoLoop, SSEv2
from ...core.v3.blackboard import SharedBlackboard

logger = logging.getLogger("dream-os.v3.api")
router = APIRouter(prefix="/api/v3/dev", tags=["v3-dev"])

_v3_tool_manager: ToolManager | None = None

# 人机协作关卡
_checkpoint_states: dict[str, dict] = {}

def get_v3_tool_manager() -> ToolManager:
    global _v3_tool_manager
    if _v3_tool_manager is None:
        _v3_tool_manager = ToolManager()
        _v3_tool_manager.register(ShellTool())
        _v3_tool_manager.register(FileTool())
        _v3_tool_manager.register(HttpTool())
    return _v3_tool_manager


class DevRequest(BaseModel):
    requirement: str
    project_id: Optional[str] = None
    max_iterations: int = 3


@router.post("/start")
async def start_dev(req: DevRequest, db: AsyncSession = Depends(get_db)):
    task_id = str(uuid.uuid4())[:8]
    dev_task = DevTask(
        id=task_id, requirement=req.requirement, status="pending",
        max_iterations=req.max_iterations, project_id=req.project_id,
    )
    db.add(dev_task); await db.commit()
    event_queue: asyncio.Queue = asyncio.Queue()

    async def gen():
        async def run_dev():
            try:
                dev_task.status = "planning"
                dev_task.workspace_path = f"/workspace/projects/{task_id}"
                await db.commit()
                tool_manager = get_v3_tool_manager()
                auto_loop = AutoLoop(tool_manager)

                async def emit(event: dict):
                    event["task_id"] = task_id
                    try:
                        if event.get("type") == "agent_start":
                            dev_task.current_agent = event.get("agent", "")
                            dev_task.status = event.get("agent", "running"); await db.commit()
                        if event.get("type") == "agent_tool_call":
                            dev_task.execution_log = (dev_task.execution_log or []) + [{
                                "agent": event.get("agent"), "tool": event.get("tool"),
                                "arguments": event.get("arguments"),
                                "iteration": event.get("iteration"),
                                "timestamp": datetime.now().isoformat(),
                            }]; await db.commit()
                        if event.get("type") == "agent_complete":
                            bb = auto_loop.get_blackboard()
                            dev_task.plan = bb.plan; dev_task.architecture = bb.architecture
                            dev_task.files = list(bb.files.keys())
                            dev_task.test_results = bb.test_results
                            dev_task.deployment = bb.deployment
                            dev_task.reports = bb.reports
                            dev_task.iteration = bb.iteration; await db.commit()
                    except Exception: pass

                    # — 人机协作: Agent 启动时暂停等待确认 —
                    if event.get("type") == "agent_start" and _checkpoint_states.get(task_id, {}).get("auto") is not True:
                        agent_name = event.get("name", event.get("agent", ""))
                        agent_emoji = event.get("emoji", "")
                        agent_task = event.get("task", "")
                        checkpoint_event = {
                            "type": "human_checkpoint",
                            "task_id": task_id,
                            "agent": event.get("agent", ""),
                            "name": agent_name,
                            "emoji": agent_emoji,
                            "task": agent_task,
                            "message": f"{agent_emoji} {agent_name} 准备开始工作，是否继续？",
                        }
                        # 发送关卡事件到前端
                        await event_queue.put(SSEv2._format(checkpoint_event))
                        # 等待用户确认
                        st = _checkpoint_states.setdefault(task_id, {})
                        st.setdefault("event", asyncio.Event())
                        await st["event"].wait()
                        st["event"].clear()
                        action = st.get("action", "proceed")
                        if action == "skip":
                            logger.info(f"Human checkpoint: {task_id} skipped {agent_name}")
                            # 不发 agent_start 给前端，直接跳过
                            return  # 不发射原始事件
                        elif action == "stop":
                            raise asyncio.CancelledError(f"用户手动停止任务: {task_id}")

                    await event_queue.put(SSEv2._format(event))

                result = await auto_loop.run(
                    requirement=req.requirement, task_id=task_id,
                    emit=emit, max_iterations=req.max_iterations,
                )
                dev_task.status = "completed" if result["success"] else "failed"
                dev_task.result = result.get("summary", "")
                dev_task.summary = result.get("summary", "")
                dev_task.completed_at = datetime.utcnow(); await db.commit()
            except Exception as e:
                logger.error(f"Dev task {task_id} failed: {e}", exc_info=True)
                dev_task.status = "failed"; dev_task.error_log = str(e)
                await db.commit()
                await event_queue.put(SSEv2.error(str(e)))
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(run_dev())
        try:
            while True:
                event_data = await event_queue.get()
                if event_data is None: break
                yield event_data
        finally:
            if not task.done(): task.cancel()
            yield SSEv2.done()

    return StreamingResponse(gen(), media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Connection":"keep-alive"})


@router.get("/tasks")
async def list_dev_tasks(status: Optional[str] = Query(None), limit: int = Query(20),
                         db: AsyncSession = Depends(get_db)):
    query = select(DevTask).order_by(desc(DevTask.created_at)).limit(limit)
    if status: query = query.where(DevTask.status == status)
    result = await db.execute(query); tasks = result.scalars().all()
    return {"tasks": [{
        "id": t.id, "requirement": t.requirement[:100], "status": t.status,
        "current_agent": t.current_agent, "iteration": t.iteration,
        "max_iterations": t.max_iterations,
        "files_count": len(t.files) if t.files else 0,
        "summary": t.summary[:200] if t.summary else "",
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "completed_at": t.completed_at.isoformat() if t.completed_at else "",
    } for t in tasks], "count": len(tasks)}


@router.get("/tasks/{task_id}")
async def get_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    return {
        "id": task.id, "requirement": task.requirement, "status": task.status,
        "current_agent": task.current_agent, "workspace_path": task.workspace_path,
        "plan": task.plan, "architecture": task.architecture, "files": task.files,
        "test_results": task.test_results, "deployment": task.deployment,
        "reports": task.reports, "execution_log": (task.execution_log or [])[-20:],
        "iteration": task.iteration, "max_iterations": task.max_iterations,
        "summary": task.summary, "error_log": task.error_log,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "completed_at": task.completed_at.isoformat() if task.completed_at else "",
    }


@router.get("/tasks/{task_id}/files")
async def get_task_files(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    from ...core.v3.workspace import Workspace
    ws = Workspace(task_id)
    if not ws.exists(): return {"files": [], "workspace": task.workspace_path}
    return {"files": ws.list_files(), "workspace": task.workspace_path, "file_tree": ws.file_tree()}


@router.get("/tasks/{task_id}/files/{filepath:path}")
async def get_task_file_content(task_id: str, filepath: str, db: AsyncSession = Depends(get_db)):
    from ...core.v3.workspace import Workspace
    ws = Workspace(task_id)
    if not ws.exists():
        return JSONResponse(status_code=404, content={"error": "工作空间不存在"})
    content = ws.read_file(filepath)
    if not content:
        full_path = os.path.join(ws.root, filepath)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f: content = f.read()
        else:
            return JSONResponse(status_code=404, content={"error": "文件不存在"})
    return {"filepath": filepath, "content": content[:10000], "size": len(content)}


@router.get("/agents")
async def list_agents():
    from ...core.v3.agents import ALL_AGENTS
    agents = [a().to_info() for a in ALL_AGENTS]
    return {"agents": agents, "count": len(agents)}


_task_controls: dict[str, dict] = {}

@router.post("/tasks/{task_id}/pause")
async def pause_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    active = ("planning","architecting","coding","executing","reviewing","testing","deploying","reporting","running")
    if task.status not in active: return JSONResponse(status_code=400, content={"error": "只能暂停运行中的任务"})
    if task_id in _task_controls: _task_controls[task_id]["paused"] = True
    task.status = "paused"; task.current_agent = "paused"; await db.commit()
    return {"status": "ok", "task_id": task_id}

@router.post("/tasks/{task_id}/resume")
async def resume_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    if task.status != "paused": return JSONResponse(status_code=400, content={"error": "只能恢复已暂停的任务"})
    if task_id in _task_controls: _task_controls[task_id]["paused"] = False
    task.status = "coding"; task.current_agent = "coding"; await db.commit()
    return {"status": "ok", "task_id": task_id}

@router.post("/tasks/{task_id}/stop")
async def stop_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    if task.status in ("completed","failed","stopped"): return JSONResponse(status_code=400, content={"error": "任务已经结束"})
    if task_id in _task_controls: del _task_controls[task_id]
    task.status = "stopped"; task.current_agent = ""; task.completed_at = datetime.utcnow(); await db.commit()
    return {"status": "ok", "task_id": task_id}

@router.delete("/tasks/{task_id}")
async def delete_dev_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    active = ("planning","coding","executing","architecting","reviewing","testing","deploying","reporting","running","paused")
    if task.status in active: return JSONResponse(status_code=400, content={"error": "只能删除已结束的任务"})
    if task_id in _task_controls: del _task_controls[task_id]
    await db.delete(task); await db.commit()
    return {"status": "ok", "task_id": task_id}

@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    order = ["planning","architecting","coding","executing","reviewing","testing","deploying","reporting"]
    total = len(order)
    idx = order.index(task.status) if task.status in order else -1
    if task.status == "completed": progress = 100
    elif task.status in ("failed","stopped","paused"): progress = int((idx)/total*100) if idx>=0 else 0
    else: progress = int((idx+1)/total*100) if idx>=0 else 0
    remaining = 0
    if task.created_at and task.status not in ("completed","failed","stopped","paused"):
        elapsed = (datetime.utcnow()-task.created_at).total_seconds()/60
        remaining = int((elapsed/idx)*(total-idx)) if idx>0 and elapsed>0.1 else total*2
    return {
        "id":task.id,"requirement":task.requirement[:200],"status":task.status,
        "current_agent":task.current_agent,"progress":progress,"iteration":task.iteration,
        "max_iterations":task.max_iterations,
        "elapsed_minutes":int((datetime.utcnow()-task.created_at).total_seconds()/60) if task.created_at else 0,
        "remaining_minutes":remaining,
        "files_count":len(task.files) if task.files else 0,
        "reports_count":len(task.reports) if task.reports else 0,
        "error":task.error_log[:200] if task.error_log else "","paused":task.status=="paused",
    }


# ════════════════════════════════════════════
# V5.2 新增: 项目环境变量管理
# ════════════════════════════════════════════

class EnvRequest(BaseModel):
    env_vars: dict[str, str] = {}  # KEY=VALUE pairs


@router.get("/tasks/{task_id}/env")
async def get_task_env(task_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目的环境变量 (从 .env 文件读取)"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})

    env_path = os.path.join(task.workspace_path or f"/workspace/projects/{task_id}", ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return {"env_vars": env_vars, "workspace": task.workspace_path}


@router.post("/tasks/{task_id}/env")
async def save_task_env(task_id: str, req: EnvRequest, db: AsyncSession = Depends(get_db)):
    """保存项目的环境变量 (写入 .env 文件)"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})

    workspace = task.workspace_path or f"/workspace/projects/{task_id}"
    os.makedirs(workspace, exist_ok=True)
    env_path = os.path.join(workspace, ".env")

    with open(env_path, "w") as f:
        f.write("# Dream OS 项目环境变量\n")
        f.write(f"# 项目: {task_id}\n")
        f.write(f"# 需求: {task.requirement[:80]}\n\n")
        for key, val in req.env_vars.items():
            f.write(f"{key}={val}\n")

    return {"status": "ok", "message": "环境变量已保存", "count": len(req.env_vars)}


# ════════════════════════════════════════════
# V5.2 新增: 部署触发 (用户指定目标)
# ════════════════════════════════════════════

class DeployRequest(BaseModel):
    target: str = "local"       # "local" | "docker"
    port: int = 8000
    command: Optional[str] = None  # 自定义启动命令


@router.post("/tasks/{task_id}/deploy")
async def deploy_task(task_id: str, req: DeployRequest, db: AsyncSession = Depends(get_db)):
    """部署项目到指定目标"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})
    # 允许失败或暂停的任务也部署，因为代码可能已经生成
    if task.status in ("pending", "running", "planning"):
        return JSONResponse(status_code=400, content={"error": "任务尚未生成代码，无法部署"})

    workspace = task.workspace_path or f"/workspace/projects/{task_id}"
    if not os.path.exists(workspace):
        return JSONResponse(status_code=404, content={"error": f"工作空间不存在: {workspace}"})

    task.status = "deploying"; await db.commit()

    try:
        if req.target == "local":
            # 查找入口文件
            entry = req.command
            if not entry:
                entry = _find_entry(workspace)

            # 构建环境变量
            env = os.environ.copy()
            env["PYTHONPATH"] = workspace + ":" + env.get("PYTHONPATH", "")

            # 加载 .env
            env_path = os.path.join(workspace, ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip().strip('"').strip("'")

            # 先安装依赖
            req_file = os.path.join(workspace, "requirements.txt")
            if os.path.exists(req_file):
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", req_file],
                        capture_output=True, text=True, timeout=120, cwd=workspace,
                    )
                except Exception as e:
                    logger.warning(f"Install deps for {task_id}: {e}")

            # 启动
            proc = subprocess.Popen(
                entry.split(), cwd=workspace,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env,
            )
            # 短暂等待看是否立即崩溃
            await asyncio.sleep(2)
            if proc.poll() is not None:
                stderr = proc.stderr.read()[:500]
                return {
                    "status": "failed",
                    "message": f"进程启动后立即退出",
                    "stderr": stderr,
                    "port": req.port,
                }

            deployment = {
                "target": "local",
                "port": req.port,
                "command": entry,
                "pid": proc.pid,
                "workspace": workspace,
            }
            task.deployment = deployment
            task.status = "completed"
            await db.commit()

            return {
                "status": "ok", "message": f"项目已在端口 {req.port} 启动",
                "deployment": deployment,
            }

        elif req.target == "docker":
            # 检查是否有 Dockerfile
            dockerfile = os.path.join(workspace, "Dockerfile")
            if not os.path.exists(dockerfile):
                return {"status": "failed", "message": "项目缺少 Dockerfile，无法Docker部署"}

            image_name = f"dream-os-task-{task_id}"
            subprocess.run(
                ["docker", "build", "-t", image_name, workspace],
                capture_output=True, text=True, timeout=120,
            )
            subprocess.run(
                ["docker", "run", "-d", "-p", f"{req.port}:{req.port}",
                 "--name", image_name, image_name],
                capture_output=True, text=True, timeout=30,
            )

            deployment = {"target": "docker", "port": req.port, "image": image_name, "workspace": workspace}
            task.deployment = deployment
            task.status = "completed"
            await db.commit()

            return {"status": "ok", "message": f"Docker 容器已启动，端口 {req.port}", "deployment": deployment}

        else:
            return {"status": "failed", "message": f"不支持的部署目标: {req.target}"}

    except Exception as e:
        logger.error(f"Deploy {task_id} failed: {e}", exc_info=True)
        task.status = "failed"
        task.error_log = str(e)
        await db.commit()
        return {"status": "failed", "message": str(e)[:300]}


def _find_entry(workspace: str) -> str:
    """自动查找项目入口文件"""
    for name in ["main.py", "app.py", "run.py", "server.py", "index.js", "manage.py"]:
        path = os.path.join(workspace, name)
        if os.path.exists(path): return f"python3 {name}"
    # 搜索 src/ 下的
    for name in ["main.py", "app.py"]:
        path = os.path.join(workspace, "src", name)
        if os.path.exists(path): return f"python3 src/{name}"
    # 找第一个 .py
    for f in sorted(os.listdir(workspace)):
        if f.endswith(".py") and f not in ["setup.py", "__init__.py"]:
            return f"python3 {f}"
    return "python3 main.py"


# ════════════════════════════════════════════
# V5.3 新增: 人机协作关卡确认
# ════════════════════════════════════════════

class HumanActionRequest(BaseModel):
    action: str = "proceed"  # "proceed" | "skip" | "auto" | "stop"
    message: str = ""


@router.post("/tasks/{task_id}/human-action")
async def human_action(task_id: str, req: HumanActionRequest, db: AsyncSession = Depends(get_db)):
    """用户对 human_checkpoint 事件的回应"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})

    st = _checkpoint_states.setdefault(task_id, {})

    if req.action == "auto":
        st["auto"] = True
        st["action"] = "proceed"
    elif req.action == "stop":
        st["action"] = "stop"
        task.status = "stopped"
        await db.commit()
    else:
        st["action"] = req.action

    # 触发等待中的 emit 回调继续执行
    evt = st.get("event")
    if evt:
        evt.set()
        return {"status": "ok", "action": req.action, "task_id": task_id}

    return {"status": "ok", "message": "无需等待", "task_id": task_id}


# ════════════════════════════════════════════
# V5.2 新增: 人机协作输入
# ════════════════════════════════════════════

class HumanInputRequest(BaseModel):
    input_type: str = "text"     # "text" | "api_key" | "password" | "confirm"
    prompt: str = ""             # 给用户的提示信息
    key: str = ""                # 关联的凭据/参数名
    value: str = ""              # 用户输入的值


@router.post("/tasks/{task_id}/human-input")
async def human_input(task_id: str, req: HumanInputRequest, db: AsyncSession = Depends(get_db)):
    """处理用户输入 — 用于人机协作关卡"""
    result = await db.execute(select(DevTask).where(DevTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task: return JSONResponse(status_code=404, content={"error": "任务不存在"})

    # 如果提供了 key 和 value，写入 .env
    if req.key and req.value:
        workspace = task.workspace_path or f"/workspace/projects/{task_id}"
        os.makedirs(workspace, exist_ok=True)
        env_path = os.path.join(workspace, ".env")

        # 读取现有
        existing_lines = []
        if os.path.exists(env_path):
            with open(env_path) as f: existing_lines = f.readlines()

        # 更新或追加
        found = False
        for i, line in enumerate(existing_lines):
            if line.strip().startswith(f"{req.key}="):
                existing_lines[i] = f"{req.key}={req.value}\n"
                found = True; break
        if not found:
            existing_lines.append(f"\n{req.key}={req.value}\n")

        with open(env_path, "w") as f: f.writelines(existing_lines)

        # 同时设置环境变量
        os.environ[req.key] = req.value

        return {"status": "ok", "message": f"已保存 {req.key}", "key": req.key}

    # 纯确认/文本输入
    # 存储到任务执行日志
    entry = {
        "type": "human_input",
        "input_type": req.input_type,
        "prompt": req.prompt,
        "value": req.value[:200] if req.value else "",
        "timestamp": datetime.now().isoformat(),
    }
    task.execution_log = (task.execution_log or []) + [entry]
    await db.commit()

    return {"status": "ok", "message": "输入已记录", "entry": entry}
