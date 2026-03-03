"""
Memory router: user preference CRUD.
"""

from fastapi import APIRouter, Header
from pydantic import BaseModel
from memory.user_memory import get_preferences, save_preferences, delete_user_memory

router = APIRouter(prefix="/api/memory", tags=["memory"])


class PreferenceUpdate(BaseModel):
    preferred_kpis: list[str] | None = None
    marketplaces: list[str] | None = None
    categories: list[str] | None = None
    analysis_style: str | None = None


@router.get("/preferences")
async def get_prefs(x_user_id: str = Header(default="default-user")):
    return await get_preferences(x_user_id)


@router.patch("/preferences")
async def update_prefs(
    updates: PreferenceUpdate,
    x_user_id: str = Header(default="default-user"),
):
    return await save_preferences(x_user_id, updates.model_dump(exclude_none=True))


@router.delete("/reset")
async def reset_memory(x_user_id: str = Header(default="default-user")):
    await delete_user_memory(x_user_id)
    return {"status": "ok", "message": "All memory wiped."}
