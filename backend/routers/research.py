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
from db.models import ResearchSession, UploadRecord, ShopifyConnection
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])


class QueryRequest(BaseModel):
    query: str
    mode: str = "quick"
    user_id: str | None = None


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
        # Chat fields (defaults for non-chat flow)
        "conversation_history": [],
        "is_followup": False,
        "chat_answer": "",
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


async def _user_has_data(user_id: str) -> bool:
    """Check if user has any uploaded or synced data before launching expensive research."""
    async with AsyncSessionLocal() as db:
        uploads = await db.execute(
            select(UploadRecord.id).where(UploadRecord.user_id == user_id).limit(1)
        )
        if uploads.scalar_one_or_none():
            return True

        shop = await db.execute(
            select(ShopifyConnection.id).where(ShopifyConnection.user_id == user_id).limit(1)
        )
        if shop.scalar_one_or_none():
            return True

    return False


@router.post("/query")
async def start_research(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(default="default-user"),
):
    """Start a research session and return session_id for SSE stream."""
    resolved_user_id = request.user_id or x_user_id

    is_clarified = "[Clarification:" in request.query
    if not is_clarified and not await _user_has_data(resolved_user_id):
        return {
            "session_id": None,
            "user_id": resolved_user_id,
            "needs_clarification": True,
            "clarification_question": (
                "I don't have any data for your account yet. "
                "Please upload your product catalog, reviews, pricing, "
                "or competitor data first, or connect your Shopify store."
            ),
        }

    session_id = str(uuid4())

    background_tasks.add_task(
        _run_agent_async,
        session_id,
        resolved_user_id,
        request.query,
        request.mode
    )

    return {"session_id": session_id, "user_id": resolved_user_id}


@router.get("/stream/{session_id}")
async def stream_progress(
    session_id: str,
    x_user_id: str = Header(default="default-user"),
):
    """SSE stream: subscribe to Redis pubsub for real-time agent progress."""
    if not session_id or session_id == "null":
        raise HTTPException(status_code=400, detail="Invalid session_id")

    async def event_generator():
        import os
        import redis.asyncio as aioredis

        try:
            r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(f"progress:{session_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for SSE: {e}")
            yield f"data: {json.dumps({'error': 'Internal server error: Redis connection failed'})}\n\n"
            return

        HEARTBEAT_INTERVAL = 15  # seconds
        MAX_STREAM_DURATION = 300  # 5 minutes max
        import time
        start_time = time.monotonic()

        try:
            while True:
                elapsed = time.monotonic() - start_time
                if elapsed > MAX_STREAM_DURATION:
                    logger.warning(f"SSE stream for {session_id} exceeded max duration ({MAX_STREAM_DURATION}s)")
                    yield f"data: {json.dumps({'step': '__done__', 'status': 'done', 'label': 'Stream timeout'})}\n\n"
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=HEARTBEAT_INTERVAL,
                    )
                except asyncio.TimeoutError:
                    # No message received within heartbeat interval — send keep-alive
                    yield ": keepalive\n\n"
                    continue

                if message is None:
                    yield ": keepalive\n\n"
                    continue

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
            "Connection": "keep-alive",
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


# ── Chat Models ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    query: str
    session_id: str
    user_id: str
    mode: str = "quick"
    conversation_history: list[ChatMessage] = []
    report_context: dict | None = None   # full report JSON for follow-ups


# ── Chat Endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat_query(
    req: ChatRequest,
    x_user_id: str = Header(default="default-user"),
):
    """Chat endpoint for follow-up questions about a report."""
    resolved_user_id = req.user_id or x_user_id
    is_followup = len(req.conversation_history) > 0

    # ── FAST PATH: follow-up with report context → direct LLM call ────────
    if is_followup and req.report_context:
        try:
            from utils.llm import call_llm_with_retry

            report = req.report_context

            # Build conversation context string
            conv_lines = []
            for m in req.conversation_history[-10:]:   # last 10 messages max
                role_label = "User" if m.role == "user" else "Analyst"
                conv_lines.append(f"{role_label}: {m.content}")
            conversation_text = "\n".join(conv_lines)

            prompt = f"""You are a senior e-commerce business analyst having a conversation with a seller.
You have already produced a detailed analysis report. Use it to answer the user's question.

═══ FULL ANALYSIS REPORT ═══
Executive Summary: {report.get('executive_summary', 'N/A')}

Key Metrics:
{json.dumps(report.get('key_metrics', {}), indent=2)}

Sentiment Breakdown:
{json.dumps(report.get('sentiment_breakdown', {}), indent=2)}

Pricing Analysis:
{json.dumps(report.get('pricing_analysis', {}), indent=2)}

Competitive Gaps:
{json.dumps(report.get('competitive_gaps', []), indent=2)}

Root Cause Analysis:
{report.get('root_cause', 'N/A')}

Recommended Actions:
{json.dumps(report.get('recommended_actions', []), indent=2)}

Follow-Up Suggestions:
{json.dumps(report.get('follow_up_suggestions', []), indent=2)}

Confidence Score: {report.get('confidence_score', 'N/A')}%
Data Completeness: {report.get('data_completeness', 'N/A')}

Reasoning Trace (Deep Analysis Steps):
{chr(10).join(report.get('reasoning_trace', [])) or 'N/A'}
═══ END OF REPORT ═══

═══ CONVERSATION SO FAR ═══
{conversation_text}
═══ END OF CONVERSATION ═══

Current Question: {req.query}

INSTRUCTIONS:
1. Answer the question thoroughly using ONLY data from the report above.
2. Always cite specific numbers, percentages, product names, and SKUs from the report.
3. When explaining WHY something is happening, reference the root cause analysis and reasoning trace.
4. If the report doesn't contain enough information to answer, say so honestly — never fabricate data.
5. Structure your answer clearly. Use bullet points or numbered lists for multiple points.
6. Keep your response concise but complete — typically 3-6 sentences, or more if the question is complex.
7. If the user asks about recommendations, reference the specific actions and their expected impacts from the report."""

            chat_answer = await asyncio.to_thread(call_llm_with_retry, prompt)

            return {
                "session_id": req.session_id,
                "report": None,
                "chat_answer": chat_answer,
                "is_followup": True,
            }
        except Exception as e:
            logger.error(f"Chat follow-up failed: {e}")
            return {
                "session_id": req.session_id,
                "report": None,
                "chat_answer": "Sorry, I encountered an error processing your question. Please try again.",
                "is_followup": True,
            }

    # ── FULL PATH: first query or no report context → run agent graph ─────
    initial_state: AgentState = {
        "session_id": req.session_id,
        "user_id": resolved_user_id,
        "query": req.query,
        "mode": "quick" if is_followup else req.mode,
        "user_preferences": {},
        "past_analyses": [],
        "catalog_chunks": [],
        "review_chunks": [],
        "pricing_chunks": [],
        "competitor_chunks": [],
        "order_chunks": [],
        "customer_chunks": [],
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
        "is_simple": False,
        "total_products_synced": 0,
        "total_orders_synced": 0,
        "total_customers_synced": 0,
        "reasoning_trace": [],
        "conversation_history": [m.model_dump() for m in req.conversation_history],
        "is_followup": is_followup,
        "chat_answer": "",
    }

    try:
        graph = get_agent_graph()
        final_state = await asyncio.to_thread(graph.invoke, initial_state)

        return {
            "session_id": req.session_id,
            "report": final_state.get("report") if not final_state.get("is_followup") else None,
            "chat_answer": final_state.get("chat_answer", ""),
            "is_followup": final_state.get("is_followup", False),
        }
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        return {
            "session_id": req.session_id,
            "report": None,
            "chat_answer": "Sorry, I encountered an error processing your question. Please try again.",
            "is_followup": True,
        }
