"""
Upload router: handles CSV/XLSX/JSON ingestion for all 4 data types.
"""

import logging

from fastapi import APIRouter, File, UploadFile, HTTPException, Header
from fastapi.responses import JSONResponse

from data.ingestion import ingest_file
from db.models import UploadRecord
from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


async def _save_upload_record(user_id: str, data_type: str, row_count: int):
    async with AsyncSessionLocal() as db:
        record = UploadRecord(user_id=user_id, data_type=data_type, row_count=row_count)
        db.add(record)
        await db.commit()


async def handle_upload(file: UploadFile, data_type: str, user_id: str) -> dict:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        result = ingest_file(contents, file.filename or "upload.csv", data_type, user_id)
        await _save_upload_record(user_id, data_type, result["rows_loaded"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error ({data_type}): {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.post("/catalog")
async def upload_catalog(
    file: UploadFile = File(...),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "catalog", x_user_id)


@router.post("/reviews")
async def upload_reviews(
    file: UploadFile = File(...),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "reviews", x_user_id)


@router.post("/pricing")
async def upload_pricing(
    file: UploadFile = File(...),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "pricing", x_user_id)


@router.post("/competitors")
async def upload_competitors(
    file: UploadFile = File(...),
    x_user_id: str = Header(default="default-user"),
):
    return await handle_upload(file, "competitors", x_user_id)
