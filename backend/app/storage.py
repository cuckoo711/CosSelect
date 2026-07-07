import re
from pathlib import Path

from .config import settings

_SAFE = re.compile(r"[^A-Za-z0-9_.\-]")


def safe_filename(name: str) -> str:
    name = name.replace("/", "_").replace("\\", "_")
    name = _SAFE.sub("_", name)
    return name[:200] or "file"


def originals_dir(space_id: int, category_id: int) -> Path:
    p = settings.data_path / str(space_id) / "originals" / str(category_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def thumbnails_dir(space_id: int, category_id: int) -> Path:
    p = settings.data_path / str(space_id) / "thumbnails" / str(category_id)
    p.mkdir(parents=True, exist_ok=True)
    return p
