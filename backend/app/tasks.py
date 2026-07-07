import io
from pathlib import Path

from celery import shared_task
from PIL import Image, ImageOps

from .config import settings
from .database import SessionLocal
from .models import Photo
from .storage import thumbnails_dir


def _build_thumbnail(src: Path, dst_dir: Path, stem: str) -> Path | None:
    """Generate a stripped-Exif thumbnail (<=1200px wide, <=500KB) as JPEG."""
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)  # honor orientation then drop Exif
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")

            w, h = im.size
            max_w = settings.thumbnail_max_width
            if w > max_w:
                new_h = int(h * max_w / w)
                im = im.resize((max_w, new_h), Image.LANCZOS)

            dst = dst_dir / f"{stem}.jpg"
            quality = settings.thumbnail_quality
            while quality >= 40:
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=quality, optimize=True)
                data = buf.getvalue()
                if len(data) <= settings.thumbnail_max_bytes or quality == 40:
                    dst.write_bytes(data)
                    return dst
                quality -= 8
    except Exception:
        return None
    return None


@shared_task(name="app.tasks.generate_thumbnail")
def generate_thumbnail(photo_id: int):
    db = SessionLocal()
    try:
        photo = db.get(Photo, photo_id)
        if not photo:
            return
        src = Path(photo.file_path)
        if not src.exists():
            return
        space_id = photo.category.space_id
        category_id = photo.category_id
        dst_dir = thumbnails_dir(space_id, category_id)
        stem = Path(photo.file_path).stem
        dst = _build_thumbnail(src, dst_dir, stem)
        if dst:
            photo.thumbnail_path = str(dst)
            db.commit()
    finally:
        db.close()


def enqueue_thumbnail(photo_id: int):
    """Best-effort enqueue; fall back to synchronous generation if broker unavailable."""
    try:
        generate_thumbnail.delay(photo_id)
    except Exception:
        try:
            generate_thumbnail(photo_id)
        except Exception:
            pass
