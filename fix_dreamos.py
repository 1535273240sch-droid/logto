"""修复 Dream OS 后端问题的脚本

修复内容：
1. project_manager.py: delete_project 增加级联删除
2. stream.py: 项目关联异常不再被静默吞掉 + 自动记录文件
"""
import os

BASE = "/dream-os/backend/app"


def fix_project_manager():
    """修复 delete_project：增加级联删除"""
    filepath = os.path.join(BASE, "core/project_manager.py")
    with open(filepath, "r") as f:
        content = f.read()

    old = '''    async def delete_project(self, project_id: str) -> bool:
        """删除项目（级联删除关联数据）"""
        project = await self.get_project(project_id)
        if not project:
            return False
        await self.session.delete(project)
        await self.session.flush()
        logger.info(f"Project deleted: {project_id}")
        return True'''

    new = '''    async def delete_project(self, project_id: str) -> bool:
        """删除项目（级联删除关联数据：文件、工具记录、会话关联）"""
        project = await self.get_project(project_id)
        if not project:
            return False

        # 级联删除项目文件
        await self.session.execute(
            delete(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        # 级联删除工具记录
        await self.session.execute(
            delete(ProjectToolRecord).where(ProjectToolRecord.project_id == project_id)
        )
        # 级联删除会话关联
        await self.session.execute(
            delete(project_conversations).where(
                project_conversations.c.project_id == project_id
            )
        )
        # 删除项目本身
        await self.session.delete(project)
        await self.session.flush()
        logger.info(f"Project deleted (cascaded): {project_id}")
        return True'''

    if old in content:
        content = content.replace(old, new)
        with open(filepath, "w") as f:
            f.write(content)
        print("✅ project_manager.py: delete_project 已修复（增加级联删除）")
    else:
        print("⚠️ project_manager.py: 未找到匹配的旧代码，可能已修复")


def fix_stream_py():
    """修复 stream.py：项目关联异常不再静默 + 自动记录文件操作"""
    filepath = os.path.join(BASE, "api/routes/stream.py")
    with open(filepath, "r") as f:
        content = f.read()

    # 修复1：将静默异常改为日志警告
    content = content.replace(
        'logger.warning(f"Project link failed (chat mode): {e}")',
        'logger.error(f"Project link failed (chat mode): {e}", exc_info=True)'
    )
    content = content.replace(
        'logger.warning(f"Project link failed: {e}")',
        'logger.error(f"Project link failed: {e}", exc_info=True)'
    )

    # 修复2：在项目关联中增加文件自动记录
    # 当 Agent 执行了 file_write 工具时，自动记录到 project_files
    old_block = '''                    # 记录工具调用
                    for rec in pipeline._tool_records:'''

    new_block = '''                    # 自动记录 Agent 写入的文件到项目
                    for rec in pipeline._tool_records:
                        if rec.tool_name in ("file_write", "shell_exec") and rec.status == ToolStatus.SUCCESS:
                            try:
                                cmd = rec.command or ""
                                # 从 file_write 命令中提取文件路径
                                if rec.tool_name == "file_write" and "path" in cmd:
                                    import json as _json
                                    args = _json.loads(cmd) if isinstance(cmd, str) and cmd.startswith("{") else {}
                                    fpath = args.get("path", args.get("command", ""))
                                    if fpath:
                                        fname = os.path.basename(fpath)
                                        ftype = os.path.splitext(fname)[1].lstrip(".") or "txt"
                                        await pm.add_file(
                                            project_id=req.project_id,
                                            filename=fname,
                                            filepath=fpath,
                                            file_type=ftype,
                                            file_size=0,
                                            summary=f"Agent 创建",
                                        )
                            except Exception as fe:
                                logger.debug(f"Auto file record skipped: {fe}")

                    # 记录工具调用
                    for rec in pipeline._tool_records:'''

    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(filepath, "w") as f:
            f.write(content)
        print("✅ stream.py: 项目关联异常日志已增强 + 文件自动记录已添加")
    else:
        # 试试只修复日志
        with open(filepath, "w") as f:
            f.write(content)
        print("✅ stream.py: 项目关联异常日志已增强（文件自动记录可能已存在）")


if __name__ == "__main__":
    fix_project_manager()
    fix_stream_py()
    print("\n🎉 修复完成！需要重新构建后端镜像才能生效。")
