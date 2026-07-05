"""修复 stream.py — 添加成果物自动生成"""
import os

filepath = os.environ.get("FILEPATH", "/dream-os/backend/app/api/routes/stream.py")
with open(filepath, "r") as f:
    content = f.read()

# 1. 在 imports 后面添加成果物相关导入
import_line = "from ...core.events import ("
if import_line in content and "artifact_engine" not in content:
    # 在 events import 前面添加
    content = content.replace(
        "from ...core.events import (",
        "from ...core.artifact_engine import artifact_engine\n"
        "from ...core.output_router import output_router\n"
        "from ...core.events import ("
    )

# 2. 在第一个 make_done 之前添加成果物生成（chat 模式，约169行）
old_done_1 = """                yield make_done(intent=intent.intent_type,
                    conversation_id=pipeline.memory.conversation_id)
                yield "data: [DONE]\\n\\n"
                return"""

new_done_1 = """                # ── 成果物自动生成（Artifact Engine V2） ──
                try:
                    artifact_plan = output_router.route(req.message, intent.intent_type)
                    if artifact_plan.artifacts:
                        yield make_content("\\n\\n---\\n📦 正在生成成果物...")
                        artifacts = await artifact_engine.generate_batch(
                            artifact_plan.to_dict(), full_response or "",
                            conversation_id=pipeline.memory.conversation_id,
                            project_id=req.project_id or "",
                        )
                        artifact_summary = []
                        for a in artifacts:
                            if a.status == "completed":
                                artifact_summary.append(f"{a.icon} {a.title} ({a.filename})")
                        if artifact_summary:
                            yield make_content("\\n\\n✅ 成果物已生成:\\n" + "\\n".join(f"  • {s}" for s in artifact_summary))
                except Exception as ae:
                    logger.warning(f"Artifact generation skipped: {ae}")

                yield make_done(intent=intent.intent_type,
                    conversation_id=pipeline.memory.conversation_id)
                yield "data: [DONE]\\n\\n"
                return"""

if old_done_1 in content:
    content = content.replace(old_done_1, new_done_1)
    print("✅ stream.py: chat 模式成果物生成已集成")
else:
    print("⚠️ stream.py: chat 模式未找到匹配点")

# 3. 在第二个 make_done 之前添加成果物生成（pipeline 模式，约339行）
old_done_2 = """            yield make_done(
                intent=intent.intent_type,
                tools_used=[r.tool_name for r in pipeline._tool_records],
                tool_count=len(pipeline._tool_records),
                conversation_id=pipeline.memory.conversation_id,
            )"""

new_done_2 = """            # ── 成果物自动生成（Artifact Engine V2） ──
            try:
                artifact_plan = output_router.route(req.message, intent.intent_type)
                if artifact_plan.artifacts:
                    yield make_content("\\n\\n---\\n📦 正在生成成果物...")
                    # 后台生成（不阻塞主流程太久）
                    artifacts = await artifact_engine.generate_batch(
                        artifact_plan.to_dict(), full_response or "",
                        conversation_id=pipeline.memory.conversation_id,
                        project_id=req.project_id or "",
                    )
                    artifact_summary = []
                    for a in artifacts:
                        if a.status == "completed":
                            artifact_summary.append(f"{a.icon} {a.title} ({a.filename})")
                    if artifact_summary:
                        yield make_content("\\n\\n✅ 成果物已生成:\\n" + "\\n".join(f"  • {s}" for s in artifact_summary))
            except Exception as ae:
                logger.warning(f"Artifact generation skipped: {ae}")

            yield make_done(
                intent=intent.intent_type,
                tools_used=[r.tool_name for r in pipeline._tool_records],
                tool_count=len(pipeline._tool_records),
                conversation_id=pipeline.memory.conversation_id,
                artifacts=[a.to_dict() for a in artifacts] if 'artifacts' in dir() else [],
            )"""

if old_done_2 in content:
    content = content.replace(old_done_2, new_done_2)
    print("✅ stream.py: pipeline 模式成果物生成已集成")
else:
    print("⚠️ stream.py: pipeline 模式未找到匹配点")

with open(filepath, "w") as f:
    f.write(content)

print("✅ stream.py 修改完成")
