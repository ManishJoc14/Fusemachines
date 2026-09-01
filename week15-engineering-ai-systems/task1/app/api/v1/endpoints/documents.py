from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.dependencies import get_ingestion_service
from app.schemas.document import IngestionResult
from app.services.ingestion import IngestionService

router = APIRouter()
COPY_BUFFER_SIZE = 1024 * 1024


def _copy_upload(source: BinaryIO, destination: Path, max_bytes: int) -> None:
    copied_bytes = 0
    with destination.open("wb") as target:
        while chunk := source.read(COPY_BUFFER_SIZE):
            copied_bytes += len(chunk)
            if copied_bytes > max_bytes:
                raise ValueError("Document exceeds the configured upload size limit")
            target.write(chunk)


@router.post(
    "/documents",
    response_model=IngestionResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> IngestionResult:
    safe_name = Path(file.filename or "document.txt").name
    file_descriptor, temporary_name = tempfile.mkstemp(suffix=Path(safe_name).suffix)
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        await file.seek(0)
        await asyncio.to_thread(
            _copy_upload,
            file.file,
            temporary_path,
            service.max_upload_bytes,
        )
        return await service.ingest(temporary_path, document_name=safe_name)
    except ValueError as exc:
        status_code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "size limit" in str(exc)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    finally:
        await file.close()
        await asyncio.to_thread(temporary_path.unlink, missing_ok=True)
