import asyncio
import threading
import os
import pathlib
from dotenv import load_dotenv

env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def run_in_thread():
    from db.session import AsyncSessionLocal
    from db.models import ShopifyConnection
    from sqlalchemy import select

    async def _get_counts():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ShopifyConnection))
            conn = result.scalars().first()
            if conn:
                return conn.products_synced, conn.orders_synced, conn.reviews_synced
        return 0,0,0

    try:
        print("Running in thread...")
        res = asyncio.run(_get_counts())
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error:", e)

t = threading.Thread(target=run_in_thread)
t.start()
t.join()
