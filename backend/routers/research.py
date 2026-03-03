"""
Research router: SSE-based agent execution + history endpoints.
"""

import asyncio
import json
import logging
import threading
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, desc

from agent.graph import get_agent_graph
from agent.state import AgentState
from db.models import ResearchSession
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])


class QueryRequest(BaseModel):
    query: str
    mode: str = "quick"


async def _run_agent_async(session_id: str, user_id: str, query: str, mode: str):
    """Run agent in background thread (LangGraph is synchronous)."""
    import asyncio
    
    initial_state: AgentState = {
        "session_id": session_id,
        "user_id": user_id,
        "query": query,
        "mode": mode,
        "user_preferences": {},
        "past_analyses": [],
        "catalog_chunks": [],
        "review_chunks": [],
        "pricing_chunks": [],
        "competitor_chunks": [],
        "sentiment_results": {},
        "pricing_results": {},
        "competitor_results": {},
        "business_synthesis": "",
        "report": {},
        "confidence_score": 0.0,
        "data_completeness": "Low",
        "total_tokens_used": 0,
        "estimated_cost_usd": 0.0,
        "needs_clarification": False,
        "clarification_question": "",
        "completed_nodes": [],
        "error": None,
    }

    try:
        graph = get_agent_graph()
        # Run sync graph in a threadpool so it doesn't block the async loop
        final_state = await asyncio.to_thread(graph.invoke, initial_state)

        # Save to PostgreSQL
        await _save_session(session_id, user_id, query, mode, final_state)

        # Signal done via Redis sentinel
        from utils.sse import get_redis
        r = get_redis()
        r.publish(f"progress:{session_id}", json.dumps({"step": "__done__", "status": "done"}))

    except Exception as e:
        logger.error(f"Agent run failed for session {session_id}: {e}")
        from utils.sse import get_redis
        r = get_redis()
        # Publish error event
        r.publish(f"progress:{session_id}", json.dumps({
            "step": "report", "status": "done",
            "label": "Partial report ready (error occurred)"
        }))
        r.publish(f"progress:{session_id}", json.dumps({"step": "__done__", "status": "done"}))


async def _save_session(session_id: str, user_id: str, query: str, mode: str, final_state: AgentState):
    """Persist completed session to PostgreSQL."""
    try:
        async with AsyncSessionLocal() as db:
            session = ResearchSession(
                session_id=session_id,
                user_id=user_id,
                query=query,
                mode=mode,
                report_json=json.dumps(final_state.get("report", {})),
                tokens_used=final_state.get("total_tokens_used", 0),
                cost_usd=0.0,
                duration_seconds=final_state.get("report", {}).get("duration_seconds", 0.0),
            )
            db.add(session)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to save session {session_id}: {e}")


@router.post("/query")
async def start_research(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(default="default-user"),
):
    """Start a research session and return session_id for SSE stream."""
    session_id = str(uuid4())

    background_tasks.add_task(
        _run_agent_async,
        session_id,
        x_user_id,
        request.query,
        request.mode
    )

    return {"session_id": session_id}


@router.get("/stream/{session_id}")
async def stream_progress(
    session_id: str,
    x_user_id: str = Header(default="default-user"),
):
    """SSE stream: subscribe to Redis pubsub for real-time agent progress."""
    async def event_generator():
        import os
        import redis.asyncio as aioredis
        
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"progress:{session_id}")

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                data_str = message["data"]
                try:
                    data = json.loads(data_str)
                except Exception:
                    continue

                yield f"data: {data_str}\n\n"

                # Sentinel: agent finished
                if data.get("step") == "__done__":
                    break

        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f"progress:{session_id}")
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_history(x_user_id: str = Header(default="default-user")):
    """Return the user's past research sessions."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ResearchSession)
            .where(ResearchSession.user_id == x_user_id)
            .order_by(desc(ResearchSession.created_at))
            .limit(50)
        )
        sessions = result.scalars().all()

        return [
            {
                "id": s.id,
                "session_id": s.session_id,
                "query": s.query,
                "mode": s.mode,
                "tokens_used": s.tokens_used,
                "cost_usd": s.cost_usd,
                "duration_seconds": s.duration_seconds,
                "created_at": s.created_at.isoformat(),
                "report": json.loads(s.report_json) if s.report_json else None,
            }
            for s in sessions
        ]


@router.get("/report/{session_id}")
async def get_report(
    session_id: str,
    x_user_id: str = Header(default="default-user"),
):
    """Fetch a specific past report by session_id."""
    logger.info(f"Fetching report for session {session_id} and user {x_user_id}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ResearchSession).where(
                ResearchSession.session_id == session_id,
                ResearchSession.user_id == x_user_id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"Report NOT FOUND for session {session_id} and user {x_user_id}")
            raise HTTPException(status_code=404, detail="Session not found.")

        return {
            "id": session.id,
            "session_id": session.session_id,
            "query": session.query,
            "mode": session.mode,
            "tokens_used": session.tokens_used,
            "cost_usd": session.cost_usd,
            "duration_seconds": session.duration_seconds,
            "created_at": session.created_at.isoformat(),
            "report": json.loads(session.report_json) if session.report_json else None,
        }
