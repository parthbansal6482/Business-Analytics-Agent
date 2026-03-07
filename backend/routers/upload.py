"""
Upload router: handles CSV/XLSX/JSON ingestion for all 4 data types.
"""

import logging

from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Form
from fastapi.responses import JSONResponse

from data.ingestion import ingest_file
from db.models import UploadRecord
from sqlalchemy import select
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.get("/status")
async def get_upload_status(x_user_id: str = Header(default="default-user")):
    """Returns a dict of data_type -> boolean (True if records exist)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UploadRecord.data_type).where(UploadRecord.user_id == x_user_id)
        )
        found_types = {r[0] for r in result.all()}
        
        return {
            "catalog": "catalog" in found_types,
            "reviews": "reviews" in found_types,
            "pricing": "pricing" in found_types,
            "competitors": "competitors" in found_types,
        }


async def _save_upload_record(user_id: str, data_type: str, row_count: int):
    async with AsyncSessionLocal() as db:
        record = UploadRecord(user_id=user_id, data_type=data_type, row_count=row_count)
        db.add(record)
        await db.commit()


async def handle_upload(file: UploadFile, data_type: str, user_id: str) -> dict:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Check previous row count so we can report how many rows were replaced
    async with AsyncSessionLocal() as db:
        prev_result = await db.execute(
            select(UploadRecord.row_count)
            .where(UploadRecord.user_id == user_id, UploadRecord.data_type == data_type)
            .order_by(UploadRecord.created_at.desc())
            .limit(1)
        )
        prev_row = prev_result.scalar()
        previous_rows = prev_row or 0

    try:
        result = ingest_file(contents, file.filename or "upload.csv", data_type, user_id)
        await _save_upload_record(user_id, data_type, result["rows_loaded"])
        return {**result, "previous_rows": previous_rows, "replaced": previous_rows > 0}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error ({data_type}): {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")



@router.post("/catalog")
async def upload_catalog(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "catalog", user_id or x_user_id)


@router.post("/reviews")
async def upload_reviews(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "reviews", user_id or x_user_id)


@router.post("/pricing")
async def upload_pricing(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "pricing", user_id or x_user_id)


@router.post("/competitors")
async def upload_competitors(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "competitors", user_id or x_user_id)
