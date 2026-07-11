import asyncio, json
from app.db.session import async_session_factory
from app.models.setting import Setting
from sqlalchemy import select

async def main():
    async with async_session_factory() as db:
        result = await db.execute(select(Setting).where(Setting.key == "ai_engine_providers"))
        row = result.scalar_one_or_none()
        if row:
            providers = json.loads(row.value)
            for p in providers:
                if p.get("enabled"):
                    key = p.get("apiKey", "")
                    print(f"name={p.get('name')} key={key[:30]}... modelId={p.get('modelId')} baseUrl={p.get('baseUrl')}")
asyncio.run(main())