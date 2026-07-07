import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import Numeric, cast, func
from sqlalchemy.orm import Session

from ..crud import category_path
from ..database import get_db
from ..deps import require_leader
from ..models import Category, Comment, CommentLike, Favorite, Photo, Rating, Space
from ..response import ok
from ..schemas import StatsRow

router = APIRouter(prefix="/api/spaces/{space_id}", tags=["stats"])


def _collect_rows(db: Session, space_id: int, space_pid: str) -> list[dict]:
    photos = (
        db.query(Photo)
        .join(Category, Category.id == Photo.category_id)
        .filter(Category.space_id == space_id)
        .all()
    )
    photo_ids = [p.id for p in photos]
    if not photo_ids:
        return []

    rating_rows = dict(
        db.query(Rating.photo_id, func.avg(cast(Rating.score, Numeric)))
        .filter(Rating.photo_id.in_(photo_ids))
        .group_by(Rating.photo_id)
        .all()
    )
    rating_cnt = dict(
        db.query(Rating.photo_id, func.count(Rating.id))
        .filter(Rating.photo_id.in_(photo_ids))
        .group_by(Rating.photo_id)
        .all()
    )
    comment_cnt = dict(
        db.query(Comment.photo_id, func.count(Comment.id))
        .filter(Comment.photo_id.in_(photo_ids))
        .group_by(Comment.photo_id)
        .all()
    )
    like_cnt = dict(
        db.query(Comment.photo_id, func.count(CommentLike.id))
        .join(CommentLike, CommentLike.comment_id == Comment.id)
        .filter(Comment.photo_id.in_(photo_ids))
        .group_by(Comment.photo_id)
        .all()
    )
    fav_cnt = dict(
        db.query(Favorite.photo_id, func.count(Favorite.id))
        .filter(Favorite.photo_id.in_(photo_ids))
        .group_by(Favorite.photo_id)
        .all()
    )

    path_cache: dict[int, str] = {}
    rows = []
    for p in photos:
        if p.category_id not in path_cache:
            path_cache[p.category_id] = category_path(db, p.category_id)
        avg = rating_rows.get(p.id)
        rows.append(
            {
                "photo_id": p.id,
                "original_name": p.original_name,
                "category_path": path_cache[p.category_id],
                "thumbnail_url": (
                    f"/api/spaces/{space_pid}/photos/{p.id}/thumbnail" if p.thumbnail_path else None
                ),
                "original_url": f"/api/spaces/{space_pid}/photos/{p.id}/original",
                "avg_score": round(float(avg), 1) if avg is not None else 0.0,
                "rating_count": int(rating_cnt.get(p.id, 0)),
                "comment_count": int(comment_cnt.get(p.id, 0)),
                "total_likes": int(like_cnt.get(p.id, 0)),
                "total_favorites": int(fav_cnt.get(p.id, 0)),
            }
        )
    rows.sort(key=lambda r: (r["avg_score"], r["rating_count"]), reverse=True)
    return rows


@router.get("/stats")
def stats_dashboard(space_id: str, space: Space = Depends(require_leader), db: Session = Depends(get_db)):
    rows = _collect_rows(db, space.id, space.public_id)
    return ok(rows)


@router.get("/export")
def export_csv(space_id: str, space: Space = Depends(require_leader), db: Session = Depends(get_db)):
    rows = _collect_rows(db, space.id, space.public_id)

    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(
        ["图片名", "分类路径", "平均分", "评分人数", "批注数", "赞同总数", "个人喜欢总数", "图片链接"]
    )
    for r in rows:
        writer.writerow(
            [
                r["original_name"],
                r["category_path"],
                r["avg_score"],
                r["rating_count"],
                r["comment_count"],
                r["total_likes"],
                r["total_favorites"],
                r["original_url"],
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cosselect_space_{space_id}.csv"'},
    )
