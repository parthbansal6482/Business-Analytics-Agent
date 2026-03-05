import asyncio
import os
import pathlib
from dotenv import load_dotenv

env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from db.session import AsyncSessionLocal
from db.models import ShopifyConnection
from sqlalchemy import select

async def check():
    print("Postgres DB Counts:")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ShopifyConnection))
        rows = res.scalars().all()
        for r in rows:
            print(f"User {r.user_id}: products={r.products_synced}, orders={r.orders_synced}, customers={r.reviews_synced}")

if __name__ == "__main__":
    asyncio.run(check())
