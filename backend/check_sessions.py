
import asyncio
import os
from sqlalchemy import select
from db.session import AsyncSessionLocal
from db.models import ResearchSession

async def check_sessions():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ResearchSession))
        sessions = result.scalars().all()
        print(f"Total sessions: {len(sessions)}")
        for s in sessions:
            print(f"Session ID: {s.session_id}, User ID: {s.user_id}, Query: {s.query}")

if __name__ == "__main__":
    asyncio.run(check_sessions())
