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
                    old_model = p.get("modelId")
                    old_key = p.get("apiKey", "")
                    print(f"Before: modelId={old_model} key={old_key[:20]}...")
                    p["modelId"] = "agnes-2.0-flash"
                    p["apiKey"] = "sk-6jGiPFPCVEWlwvTxgDG06HGiXiAJIKvX3nmPUag6oKR053M9"
                    print(f"After: modelId={p['modelId']} key={p['apiKey'][:20]}...")
            row.value = json.dumps(providers, ensure_ascii=False)
            await db.commit()
            print("Updated providers successfully")
asyncio.run(main())