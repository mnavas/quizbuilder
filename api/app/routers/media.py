import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.config import settings
from app.db import get_db
from app.models.core import MediaFile, User

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm",
    "video/mp4", "video/webm", "video/ogg",
}

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 1024 * 256  # 256 KB chunks for streaming


def _media_id() -> str:
    return str(uuid.uuid4())


class MediaOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    url: str


def _to_out(m: MediaFile) -> MediaOut:
    return MediaOut(
        id=m.id,
        filename=m.filename,
        mime_type=m.mime_type,
        size_bytes=m.size_bytes,
        url=f"/api/v1/media/{m.id}",
    )


@router.post("", response_model=MediaOut, status_code=201)
async def upload_media(
    file: UploadFile,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    media_id = _media_id()
    safe_filename = os.path.basename(file.filename or "upload")
    rel_path = f"{user.tenant_id}/{media_id}/{safe_filename}"
    full_path = Path(settings.media_root) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)

    record = MediaFile(
        id=media_id,
        tenant_id=user.tenant_id,
        filename=safe_filename,
        mime_type=file.content_type,
        size_bytes=len(data),
        storage_path=str(rel_path),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _to_out(record)


@router.get("/{media_id}")
async def serve_media(
    media_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serve a media file with HTTP range request support for audio/video streaming."""
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Media not found")

    full_path = Path(settings.media_root) / m.storage_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    file_size = full_path.stat().st_size
    is_streaming = m.mime_type.startswith(("audio/", "video/"))

    # Images and non-streaming types: simple FileResponse
    if not is_streaming:
        return FileResponse(
            str(full_path),
            media_type=m.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{m.filename}"'},
        )

    # Audio / video: handle Range requests for browser player compatibility
    range_header = request.headers.get("range")

    if range_header:
        # Parse "bytes=start-end"
        try:
            range_val = range_header.replace("bytes=", "")
            start_str, _, end_str = range_val.partition("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except ValueError:
            raise HTTPException(status_code=416, detail="Invalid Range header")

        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )

        chunk_length = end - start + 1

        def iter_file():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = chunk_length
                while remaining > 0:
                    data = f.read(min(CHUNK_SIZE, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=m.mime_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_length),
                "Content-Disposition": f'inline; filename="{m.filename}"',
            },
        )

    # No Range header — serve full file with streaming
    def iter_full():
        with open(full_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        iter_full(),
        status_code=200,
        media_type=m.mime_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{m.filename}"',
        },
    )

