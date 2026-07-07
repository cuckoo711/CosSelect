import io
from pathlib import Path

from celery import shared_task
from PIL import Image, ImageOps

from .config import settings
from .database import SessionLocal
from .models import Photo
from .storage import thumbnails_dir


def _compress_stored_image(src: Path) -> tuple[int, str] | None:
    """Downscale the stored image to <= image_max_pixels and re-encode as JPEG,
    stripping Exif. Returns (new_file_size, new_path) or None if it failed."""
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)  # honor orientation, then drop Exif
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")

            w, h = im.size
            max_px = settings.image_max_pixels
            if w * h > max_px:
                scale = (max_px / (w * h)) ** 0.5
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                im = im.resize((new_w, new_h), Image.LANCZOS)

            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=settings.image_quality, optimize=True)
            data = buf.getvalue()

        # write compressed bytes to a .jpg alongside, then replace original
        dst = src.with_suffix(".jpg")
        dst.write_bytes(data)
        if dst != src and src.exists():
            src.unlink(missing_ok=True)
        return len(data), str(dst)
    except Exception:
        return None


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


@shared_task(name="app.tasks.process_photo")
def process_photo(photo_id: int):
    """Compress the uploaded image to <=5MP, then generate its thumbnail."""
    db = SessionLocal()
    try:
        photo = db.get(Photo, photo_id)
        if not photo:
            return
        src = Path(photo.file_path)
        if not src.exists():
            return

        # 1) compress the stored image in place
        result = _compress_stored_image(src)
        if result:
            new_size, new_path = result
            photo.file_path = new_path
            photo.file_size = new_size
            db.commit()
            src = Path(new_path)

        # 2) build thumbnail from the (compressed) stored image
        space_id = photo.category.space_id
        category_id = photo.category_id
        dst_dir = thumbnails_dir(space_id, category_id)
        stem = src.stem
        dst = _build_thumbnail(src, dst_dir, stem)
        if dst:
            photo.thumbnail_path = str(dst)
            db.commit()
    finally:
        db.close()


def enqueue_processing(photo_id: int):
    """Best-effort enqueue; fall back to synchronous processing if broker unavailable."""
    try:
        process_photo.delay(photo_id)
    except Exception:
        try:
            process_photo(photo_id)
        except Exception:
            pass
