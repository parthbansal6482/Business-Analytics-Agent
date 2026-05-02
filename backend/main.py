import os
import pathlib
from dotenv import load_dotenv

# Explicitly load .env from the same directory as main.py
env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import logging
import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.init import init_db
from memory.qdrant_store import init_collections
from data.embedder import get_embedder
from agent.graph import get_agent_graph

from routers import upload, research, memory, shopify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    # Init PostgreSQL tables
    await init_db()
    logger.info("✅ PostgreSQL tables ready")

    # Init Qdrant collections
    init_collections()
    logger.info("✅ Qdrant collections ready")

    # Warm up embedder
    get_embedder()
    logger.info("✅ Sentence-transformers embedder loaded")

    # Warm up LangGraph agent
    get_agent_graph()
    logger.info("✅ LangGraph agent compiled")

    logger.info("🚀 Backend ready!")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="E-Commerce Intelligence Research Agent",
    description="AI-powered business research with LangGraph + Gemini 2.0 Flash",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server + production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
    ] + [
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router)
app.include_router(research.router)
app.include_router(memory.router)
app.include_router(shopify.router)




@app.get("/api/health")
async def health():
    """Health check including Qdrant and DB connectivity."""
    from memory.qdrant_store import client as qdrant_client
    from db.session import engine

    qdrant_ok = False
    db_ok = False

    try:
        qdrant_client.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "qdrant": "ok" if qdrant_ok else "error",
        "database": "ok" if db_ok else "error",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
