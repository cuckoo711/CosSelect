import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .database import SessionLocal
from .models import Space


def _destroy_space_files(space_id: int):
    """Remove all on-disk assets for a space (originals + thumbnails)."""
    space_dir = Path(settings.data_dir) / str(space_id)
    if space_dir.exists():
        shutil.rmtree(space_dir, ignore_errors=True)


def cleanup_inactive_spaces() -> int:
    """Delete spaces with no access for >= inactive_destroy_days. Returns count."""
    cutoff = datetime.utcnow() - timedelta(days=settings.inactive_destroy_days)
    db = SessionLocal()
    removed = 0
    try:
        stale = db.query(Space).filter(Space.last_access_at < cutoff).all()
        for space in stale:
            sid = space.id
            db.delete(space)  # cascades to categories/photos/participants/etc.
            db.commit()
            _destroy_space_files(sid)  # remove files after DB row is gone
            removed += 1
    except Exception:
        db.rollback()
    finally:
        db.close()
    return removed


def _loop():
    interval = max(1, settings.cleanup_interval_hours) * 3600
    while True:
        try:
            cleanup_inactive_spaces()
        except Exception:
            pass
        time.sleep(interval)


def start_cleanup_thread():
    """Run an initial sweep, then periodically in a daemon thread."""
    t = threading.Thread(target=_loop, name="cosselect-cleanup", daemon=True)
    t.start()
    return t
