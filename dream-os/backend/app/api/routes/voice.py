"""语音识别 API — 用 OpenAI Whisper API 转文字"""
import os
import tempfile
import subprocess
import json
from fastapi import APIRouter, UploadFile, File

router = APIRouter()

# Whisper API 配置 — 和你的模型设置共用同一个 base_url + api_key
WHISPER_MODEL = "whisper-1"


@router.post("/api/voice/asr")
async def voice_asr(audio: UploadFile = File(...)):
    from ...db.session import async_session_factory
    from sqlalchemy import text

    # 从 DB 读取当前配置
    base_url = "https://api.openai.com/v1"
    api_key = ""
    try:
        async with async_session_factory() as db:
            rows = await db.execute(text(
                "SELECT key, value FROM settings WHERE key IN ('model_base_url','model_api_key')"
            ))
            for r in rows.fetchall():
                if r[0] == "model_base_url" and r[1]:
                    base_url = r[1].rstrip("/") if r[1] else base_url
                if r[0] == "model_api_key" and r[1]:
                    api_key = r[1]
    except Exception:
        pass

    # 保存音频文件
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        # 调 Whisper API
        whisper_url = f"{base_url}/audio/transcriptions"
        result = subprocess.run([
            "curl", "-s", "--max-time", "30",
            "-X", "POST", whisper_url,
            "-H", f"Authorization: Bearer {api_key}",
            "-F", f"file=@{tmp_path}",
            "-F", f"model={WHISPER_MODEL}",
            "-F", "language=zh",
        ], capture_output=True, text=True, timeout=35)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            text = data.get("text", "")
            return {"recognized_text": text, "status": "ok"}
        else:
            return {"recognized_text": "", "status": "error", "error": result.stderr[:200]}
    except json.JSONDecodeError:
        return {"recognized_text": "", "status": "error", "error": result.stdout[:200]}
    except Exception as e:
        return {"recognized_text": "", "status": "error", "error": str(e)[:200]}
    finally:
        os.remove(tmp_path)
