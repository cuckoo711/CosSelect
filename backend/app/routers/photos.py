from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..crud import (
    my_favorites_set,
    my_scores_map,
    photo_stats_map,
)
from ..database import get_db
from ..deps import Actor, get_actor, require_leader
from ..models import Category, Photo, Rating, Space
from ..response import ApiError, ok
from ..schemas import PhotoOut
from ..storage import originals_dir, safe_filename
from ..tasks import enqueue_thumbnail

router = APIRouter(prefix="/api/spaces/{space_id}/photos", tags=["photos"])

_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".heic"}


def _thumb_url(space_id: int, photo: Photo) -> str | None:
    if not photo.thumbnail_path:
        return None
    return f"/api/spaces/{space_id}/photos/{photo.id}/thumbnail"


def _orig_url(space_id: int, photo: Photo) -> str:
    return f"/api/spaces/{space_id}/photos/{photo.id}/original"


@router.post("/upload")
async def upload_photos(
    space_id: int,
    category_id: int = Form(...),
    files: list[UploadFile] = File(...),
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)
    if not category or category.space_id != space_id:
        raise ApiError("目标分类不存在", code=404, status_code=404)

    dest_dir = originals_dir(space_id, category_id)
    created = []
    for uf in files:
        ext = Path(uf.filename or "").suffix.lower()
        if ext and ext not in _ALLOWED_EXT:
            continue
        # unique on-disk name
        base = safe_filename(Path(uf.filename or "image").stem)
        import uuid

        disk_name = f"{base}_{uuid.uuid4().hex[:8]}{ext or '.jpg'}"
        dest = dest_dir / disk_name

        size = 0
        with dest.open("wb") as out:
            while chunk := await uf.read(1024 * 1024):
                out.write(chunk)
                size += len(chunk)

        photo = Photo(
            category_id=category_id,
            original_name=uf.filename or disk_name,
            file_path=str(dest),
            thumbnail_path=None,
            file_size=size,
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        enqueue_thumbnail(photo.id)
        created.append({"id": photo.id, "original_name": photo.original_name, "file_size": size})

    return ok({"count": len(created), "photos": created})


@router.get("")
def list_photos(
    space_id: int,
    category_id: int = Query(...),
    sort: str = Query("score", pattern="^(score|time|count)$"),
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)
    if not category or category.space_id != space_id:
        raise ApiError("分类不存在", code=404, status_code=404)

    photos = db.query(Photo).filter(Photo.category_id == category_id).all()
    photo_ids = [p.id for p in photos]
    stats = photo_stats_map(db, photo_ids)
    my_scores = my_scores_map(db, photo_ids, actor.participant_id)
    my_favs = my_favorites_set(db, photo_ids, actor.participant_id)

    items = []
    for p in photos:
        st = stats.get(p.id, {"avg_score": 0.0, "rating_count": 0, "comment_count": 0})
        items.append(
            PhotoOut(
                id=p.id,
                category_id=p.category_id,
                original_name=p.original_name,
                file_size=p.file_size,
                upload_time=p.upload_time,
                thumbnail_url=_thumb_url(space_id, p),
                original_url=_orig_url(space_id, p),
                avg_score=st["avg_score"],
                rating_count=st["rating_count"],
                comment_count=st["comment_count"],
                my_score=my_scores.get(p.id),
                my_favorite=p.id in my_favs,
            ).model_dump()
        )

    if sort == "score":
        items.sort(key=lambda x: (x["avg_score"], x["rating_count"]), reverse=True)
    elif sort == "time":
        items.sort(key=lambda x: x["upload_time"], reverse=True)
    elif sort == "count":
        items.sort(key=lambda x: (x["rating_count"], x["avg_score"]), reverse=True)

    return ok(items)


@router.get("/{photo_id}/thumbnail")
def get_thumbnail(space_id: int, photo_id: int, db: Session = Depends(get_db)):
    photo = _get_space_photo(db, space_id, photo_id)
    if photo.thumbnail_path and Path(photo.thumbnail_path).exists():
        return FileResponse(photo.thumbnail_path)
    # fallback to original when thumbnail not ready yet
    return FileResponse(photo.file_path)


@router.get("/{photo_id}/original")
def get_original(space_id: int, photo_id: int, download: bool = False, db: Session = Depends(get_db)):
    photo = _get_space_photo(db, space_id, photo_id)
    if not Path(photo.file_path).exists():
        raise ApiError("原图不存在", code=404, status_code=404)
    filename = photo.original_name if download else None
    return FileResponse(
        photo.file_path,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{photo.original_name}"'}
        if download
        else None,
    )


@router.delete("/{photo_id}")
def delete_photo(
    space_id: int,
    photo_id: int,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    photo = _get_space_photo(db, space_id, photo_id)
    for p in (photo.file_path, photo.thumbnail_path):
        if p:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
    db.delete(photo)
    db.commit()
    return ok({"deleted": photo_id})


def _get_space_photo(db: Session, space_id: int, photo_id: int) -> Photo:
    photo = (
        db.query(Photo)
        .join(Category, Category.id == Photo.category_id)
        .filter(Photo.id == photo_id, Category.space_id == space_id)
        .first()
    )
    if not photo:
        raise ApiError("图片不存在", code=404, status_code=404)
    return photo
