"""Image Tool — 图片生成工具"""
import json
import logging
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.image")


class ImageTool(BaseTool):
    """图片生成工具 — 调用 AI 生成图片"""

    name = "image_generate"
    description = "生成图片（根据文字描述创建图片）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行图片生成

        command 格式:
            image:一只可爱的猫
            image:山水画风格
        """
        try:
            prompt = command.replace("image:", "").strip()
            if not prompt:
                return ToolResult(success=False, stderr="请提供图片描述")
            return await self._generate_image(prompt)
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ToolResult(
                success=False,
                stderr=f"图片生成失败: {str(e)[:200]}",
                exit_code=1,
            )

    async def _generate_image(self, prompt: str) -> ToolResult:
        """调用 AI 图片生成 API"""
        import httpx
        from ..config import get_settings

        settings = get_settings()
        api_key = settings.openai_api_key
        base_url = settings.openai_base_url

        # 使用 OpenAI 兼容的图片生成 API
        url = f"{base_url.rstrip('/')}/v1/images/generations"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model or "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard",
                },
            )

            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                image_url = data["data"][0].get("url", "")
                revised_prompt = data["data"][0].get("revised_prompt", "")

                result = json.dumps({
                    "image_url": image_url,
                    "revised_prompt": revised_prompt,
                    "prompt": prompt,
                    "success": True,
                }, ensure_ascii=False)

                return ToolResult(success=True, stdout=result)
            else:
                error = data.get("error", {}).get("message", str(data))
                return ToolResult(
                    success=False,
                    stderr=f"图片生成 API 返回错误: {error[:300]}",
                )