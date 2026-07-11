"""Image Tool — 图片生成工具

使用 Pollinations.ai 免费 API（无需 API Key），支持多种风格。
当用户说"画/生成/创建一张图片"时触发。
"""
import json
import logging
import urllib.parse
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.image")

# 风格映射
STYLE_PROMPTS = {
    "赛博朋克": "cyberpunk, neon lights, dark atmosphere, futuristic city, vibrant colors",
    "水墨": "ink wash painting, traditional Chinese painting, brush strokes, black ink",
    "油画": "oil painting, rich textures, impasto, classic art style",
    "水彩": "watercolor, soft colors, flowing washes, paper texture",
    "素描": "pencil sketch, black and white, hand-drawn, shading",
    "像素": "pixel art, 8-bit style, retro game, blocky pixels",
    "动漫": "anime style, cel shading, vibrant colors, Japanese animation",
    "写实": "photorealistic, highly detailed, realistic lighting, 8K UHD",
    "3D": "3D render, C4D, blender, volumetric lighting, octane render",
    "卡通": "cartoon style, flat colors, cute, simple shapes",
}


class ImageTool(BaseTool):
    """图片生成工具 — 调用 Pollinations.ai 免费 API 生成图片"""

    name = "image_generate"
    description = "生成图片（根据文字描述创建图片）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行图片生成

        command 格式:
            image:一只可爱的猫
            image:赛博朋克风格的都市
            也可以带风格: 画一张水墨风格的山水画
        """
        try:
            prompt = command.replace("image:", "").replace("画一张", "").replace("生成", "").strip()
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
        """调用 Pollinations.ai 免费 API 生成图片"""
        import httpx

        # 检查是否包含风格关键词
        style_prompt = ""
        prompt_lower = prompt.lower()
        for style_cn, style_en in STYLE_PROMPTS.items():
            if style_cn in prompt_lower:
                style_prompt = f", {style_en}"
                break

        # 构建最终 prompt（英文效果更好，但中文也支持）
        full_prompt = f"{prompt}{style_prompt}"

        encoded = urllib.parse.quote(full_prompt)

        # Pollinations.ai 直接返回图片（无需 API Key）
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&seed={hash(prompt) % 100000}"

        # 验证图片 URL 可访问
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.head(image_url, follow_redirects=True)
                if resp.status_code != 200:
                    logger.warning(f"Pollinations HEAD returned {resp.status_code}, using URL anyway")
        except Exception as e:
            logger.warning(f"Pollinations verification failed: {e}")

        result = json.dumps({
            "image_url": image_url,
            "prompt": prompt,
            "style_prompt": style_prompt,
            "success": True,
            "tip": "右键图片 → 保存为图片即可下载",
        }, ensure_ascii=False)

        return ToolResult(success=True, stdout=result)