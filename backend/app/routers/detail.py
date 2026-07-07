from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..crud import (
    my_comment_likes_set,
    my_favorites_set,
    my_scores_map,
    photo_stats_map,
)
from ..database import get_db
from ..deps import Actor, get_actor
from ..models import Category, Comment, Photo
from ..response import ApiError, ok
from ..schemas import CommentOut, PhotoDetail

router = APIRouter(prefix="/api/spaces/{space_id}/photos", tags=["photo-detail"])


@router.get("/{photo_id}")
def photo_detail(
    space_id: str,
    photo_id: int,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    sid = actor.space_id
    space_pid = actor.space_public_id
    photo = (
        db.query(Photo)
        .join(Category, Category.id == Photo.category_id)
        .filter(Photo.id == photo_id, Category.space_id == sid)
        .first()
    )
    if not photo:
        raise ApiError("图片不存在", code=404, status_code=404)

    stats = photo_stats_map(db, [photo_id]).get(
        photo_id, {"avg_score": 0.0, "rating_count": 0, "comment_count": 0}
    )
    my_score = my_scores_map(db, [photo_id], actor.participant_id).get(photo_id)
    my_fav = photo_id in my_favorites_set(db, [photo_id], actor.participant_id)

    comments = db.query(Comment).filter(Comment.photo_id == photo_id).all()
    liked = my_comment_likes_set(db, [c.id for c in comments], actor.participant_id)
    comments.sort(key=lambda c: (0 if c.is_pinned else 1, -c.id))

    def author(c: Comment) -> str:
        if c.is_leader:
            return "团长"
        return c.participant.nickname if c.participant else "已退出"

    def can_edit(c: Comment) -> bool:
        if actor.is_leader:
            return c.is_leader
        return (not c.is_leader) and c.participant_id == actor.participant_id

    comment_list = [
        CommentOut(
            id=c.id,
            photo_id=c.photo_id,
            author=author(c),
            is_leader=c.is_leader,
            is_pinned=c.is_pinned,
            content=c.content,
            likes_count=c.likes_count,
            liked_by_me=c.id in liked,
            can_edit=can_edit(c),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in comments
    ]

    detail = PhotoDetail(
        id=photo.id,
        category_id=photo.category_id,
        original_name=photo.original_name,
        file_size=photo.file_size,
        upload_time=photo.upload_time,
        thumbnail_url=(
            f"/api/spaces/{space_pid}/photos/{photo.id}/thumbnail" if photo.thumbnail_path else None
        ),
        image_url=f"/api/spaces/{space_pid}/photos/{photo.id}/image",
        avg_score=stats["avg_score"],
        rating_count=stats["rating_count"],
        comment_count=stats["comment_count"],
        my_score=my_score,
        my_favorite=my_fav,
        comments=comment_list,
    )
    return ok(detail.model_dump())
