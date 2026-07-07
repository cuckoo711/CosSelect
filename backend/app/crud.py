from sqlalchemy import Numeric, cast, func
from sqlalchemy.orm import Session

from .models import Category, Comment, CommentLike, Favorite, Photo, Rating


def photo_stats_map(db: Session, photo_ids: list[int]) -> dict[int, dict]:
    """Return {photo_id: {avg_score, rating_count, comment_count}} for given photos."""
    if not photo_ids:
        return {}

    rating_rows = (
        db.query(
            Rating.photo_id,
            func.avg(cast(Rating.score, Numeric)).label("avg_score"),
            func.count(Rating.id).label("cnt"),
        )
        .filter(Rating.photo_id.in_(photo_ids))
        .group_by(Rating.photo_id)
        .all()
    )
    comment_rows = (
        db.query(Comment.photo_id, func.count(Comment.id).label("cnt"))
        .filter(Comment.photo_id.in_(photo_ids))
        .group_by(Comment.photo_id)
        .all()
    )

    result: dict[int, dict] = {
        pid: {"avg_score": 0.0, "rating_count": 0, "comment_count": 0} for pid in photo_ids
    }
    for pid, avg_score, cnt in rating_rows:
        result[pid]["avg_score"] = round(float(avg_score), 1) if avg_score is not None else 0.0
        result[pid]["rating_count"] = int(cnt)
    for pid, cnt in comment_rows:
        result[pid]["comment_count"] = int(cnt)
    return result


def my_scores_map(db: Session, photo_ids: list[int], participant_id: int | None) -> dict[int, float]:
    if not photo_ids or participant_id is None:
        return {}
    rows = (
        db.query(Rating.photo_id, Rating.score)
        .filter(Rating.photo_id.in_(photo_ids), Rating.participant_id == participant_id)
        .all()
    )
    return {pid: float(score) for pid, score in rows}


def my_favorites_set(db: Session, photo_ids: list[int], participant_id: int | None) -> set[int]:
    if not photo_ids or participant_id is None:
        return set()
    rows = (
        db.query(Favorite.photo_id)
        .filter(Favorite.photo_id.in_(photo_ids), Favorite.participant_id == participant_id)
        .all()
    )
    return {r[0] for r in rows}


def my_comment_likes_set(db: Session, comment_ids: list[int], participant_id: int | None) -> set[int]:
    if not comment_ids or participant_id is None:
        return set()
    rows = (
        db.query(CommentLike.comment_id)
        .filter(
            CommentLike.comment_id.in_(comment_ids),
            CommentLike.participant_id == participant_id,
        )
        .all()
    )
    return {r[0] for r in rows}


def category_path(db: Session, category_id: int) -> str:
    """Build 'parent / child / leaf' path string."""
    parts: list[str] = []
    cur = db.get(Category, category_id)
    guard = 0
    while cur and guard < 50:
        parts.append(cur.name)
        cur = db.get(Category, cur.parent_id) if cur.parent_id else None
        guard += 1
    return " / ".join(reversed(parts))


def descendant_category_ids(db: Session, space_id: int, root_id: int | None) -> list[int]:
    """All category ids under root (inclusive). If root is None, return all in space."""
    cats = db.query(Category.id, Category.parent_id).filter(Category.space_id == space_id).all()
    children: dict[int | None, list[int]] = {}
    for cid, pid in cats:
        children.setdefault(pid, []).append(cid)

    if root_id is None:
        return [cid for cid, _ in cats]

    result: list[int] = []
    stack = [root_id]
    while stack:
        node = stack.pop()
        result.append(node)
        stack.extend(children.get(node, []))
    return result
