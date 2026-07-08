"""Workspace — 项目工作空间管理

每个开发任务拥有独立的工作空间:
  /workspace/projects/{dev_task_id}/
  ├── src/              # 项目源码
  ├── tests/            # 测试文件
  ├── docs/             # 文档
  ├── logs/             # 执行日志
  ├── docker/           # Docker 配置
  └── .dream/           # Dream OS 元数据
      ├── state.json    # 当前状态
      └── history.jsonl # 操作历史
"""
import os
import json
import shutil
import logging
from datetime import datetime

logger = logging.getLogger("dream-os.v3.workspace")

WORKSPACE_ROOT = os.environ.get("DREAM_WORKSPACE_ROOT", "/workspace/projects")


class Workspace:
    """项目工作空间管理器"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.root = os.path.join(WORKSPACE_ROOT, task_id)
        self.src_dir = os.path.join(self.root, "src")
        self.tests_dir = os.path.join(self.root, "tests")
        self.docs_dir = os.path.join(self.root, "docs")
        self.logs_dir = os.path.join(self.root, "logs")
        self.docker_dir = os.path.join(self.root, "docker")
        self.dream_dir = os.path.join(self.root, ".dream")

    def init(self) -> str:
        """初始化工作空间目录结构"""
        for d in [self.root, self.src_dir, self.tests_dir, self.docs_dir,
                  self.logs_dir, self.docker_dir, self.dream_dir]:
            os.makedirs(d, exist_ok=True)

        # 初始化 state.json
        state_file = os.path.join(self.dream_dir, "state.json")
        if not os.path.exists(state_file):
            with open(state_file, "w") as f:
                json.dump({
                    "task_id": self.task_id,
                    "created_at": datetime.now().isoformat(),
                    "status": "initialized",
                }, f, ensure_ascii=False, indent=2)

        logger.info(f"Workspace initialized: {self.root}")
        return self.root

    def exists(self) -> bool:
        return os.path.isdir(self.root)

    def get_path(self) -> str:
        """获取工作空间根路径"""
        return self.root

    def get_src_path(self) -> str:
        return self.src_dir

    def write_file(self, relative_path: str, content: str) -> str:
        """写入文件 (相对于 src/ 目录)"""
        full_path = os.path.join(self.src_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return full_path

    def read_file(self, relative_path: str) -> str:
        """读取文件 (相对于 src/ 目录)"""
        full_path = os.path.join(self.src_dir, relative_path)
        if not os.path.exists(full_path):
            return ""
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self, subdir: str = "src") -> list[dict]:
        """列出工作空间文件"""
        target_dir = os.path.join(self.root, subdir) if subdir != "root" else self.root
        if not os.path.isdir(target_dir):
            return []

        files = []
        for root, dirs, filenames in os.walk(target_dir):
            # 跳过隐藏目录和 node_modules
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"]
            for fn in filenames:
                full_path = os.path.join(root, fn)
                rel_path = os.path.relpath(full_path, self.root)
                size = os.path.getsize(full_path)
                files.append({
                    "path": rel_path,
                    "size": size,
                    "size_text": f"{size}B" if size < 1024 else f"{size/1024:.1f}KB",
                })
        return files

    def save_log(self, log_name: str, content: str):
        """保存执行日志"""
        log_path = os.path.join(self.logs_dir, f"{log_name}.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(content)

    def save_state(self, state: dict):
        """保存状态"""
        state_file = os.path.join(self.dream_dir, "state.json")
        state["updated_at"] = datetime.now().isoformat()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self) -> dict:
        """加载状态"""
        state_file = os.path.join(self.dream_dir, "state.json")
        if not os.path.exists(state_file):
            return {}
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def cleanup(self):
        """清理工作空间"""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
            logger.info(f"Workspace cleaned: {self.root}")

    def file_tree(self) -> str:
        """生成文件树文本"""
        if not os.path.isdir(self.root):
            return "(空)"

        lines = []
        for root, dirs, files in os.walk(self.root):
            dirs[:] = sorted([d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"])
            level = root.replace(self.root, "").count(os.sep)
            indent = "  " * level
            basename = os.path.basename(root) or "."
            lines.append(f"{indent}{basename}/")
            sub_indent = "  " * (level + 1)
            for fn in sorted(files):
                lines.append(f"{sub_indent}{fn}")
        return "\n".join(lines[:100])  # 限制100行
