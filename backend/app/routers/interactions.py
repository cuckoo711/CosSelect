from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import Numeric, cast, func
from sqlalchemy.orm import Session

from ..crud import my_comment_likes_set
from ..database import get_db
from ..deps import Actor, get_actor
from ..models import Category, Comment, CommentLike, Favorite, Photo, Rating
from ..response import ApiError, ok
from ..schemas import (
    CommentIn,
    CommentOut,
    FavoriteResp,
    LikeResp,
    RatingIn,
    RatingResp,
)

router = APIRouter(prefix="/api", tags=["interactions"])


def _photo_in_space(db: Session, space_id: int, photo_id: int) -> Photo:
    photo = (
        db.query(Photo)
        .join(Category, Category.id == Photo.category_id)
        .filter(Photo.id == photo_id, Category.space_id == space_id)
        .first()
    )
    if not photo:
        raise ApiError("图片不存在", code=404, status_code=404)
    return photo


def _avg_and_count(db: Session, photo_id: int) -> tuple[float, int]:
    row = (
        db.query(func.avg(cast(Rating.score, Numeric)), func.count(Rating.id))
        .filter(Rating.photo_id == photo_id)
        .first()
    )
    avg = round(float(row[0]), 1) if row and row[0] is not None else 0.0
    cnt = int(row[1]) if row else 0
    return avg, cnt


# ---------------- Ratings ----------------
@router.post("/spaces/{space_id}/photos/{photo_id}/ratings")
def submit_rating(
    space_id: str,
    photo_id: int,
    payload: RatingIn,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    _photo_in_space(db, actor.space_id, photo_id)
    if actor.is_leader:
        raise ApiError("团长不参与评分")

    rating = (
        db.query(Rating)
        .filter(Rating.photo_id == photo_id, Rating.participant_id == actor.participant_id)
        .first()
    )
    if rating:
        rating.score = Decimal(str(payload.score))
    else:
        rating = Rating(
            photo_id=photo_id,
            participant_id=actor.participant_id,
            score=Decimal(str(payload.score)),
        )
        db.add(rating)
    db.commit()

    avg, cnt = _avg_and_count(db, photo_id)
    return ok(
        RatingResp(photo_id=photo_id, avg_score=avg, rating_count=cnt, my_score=payload.score).model_dump()
    )


# ---------------- Comments ----------------
def _serialize_comment(c: Comment, actor: Actor, liked: bool) -> dict:
    can_edit = (actor.is_leader and c.is_leader) or (
        not actor.is_leader and c.participant_id == actor.participant_id
    )
    return CommentOut(
        id=c.id,
        photo_id=c.photo_id,
        author=_comment_author(c),
        is_leader=c.is_leader,
        is_pinned=c.is_pinned,
        content=c.content,
        likes_count=c.likes_count,
        liked_by_me=liked,
        can_edit=can_edit,
        created_at=c.created_at,
        updated_at=c.updated_at,
    ).model_dump()


def _comment_author(c: Comment) -> str:
    if c.is_leader:
        return "团长"
    return c.participant.nickname if c.participant else "已退出"


@router.get("/spaces/{space_id}/photos/{photo_id}/comments")
def list_comments(
    space_id: str,
    photo_id: int,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    _photo_in_space(db, actor.space_id, photo_id)
    comments = db.query(Comment).filter(Comment.photo_id == photo_id).all()
    liked = my_comment_likes_set(db, [c.id for c in comments], actor.participant_id)
    # pinned first, then by created desc
    comments.sort(key=lambda c: (0 if c.is_pinned else 1, -c.id))
    return ok([_serialize_comment(c, actor, c.id in liked) for c in comments])


@router.post("/spaces/{space_id}/photos/{photo_id}/comments")
def create_comment(
    space_id: str,
    photo_id: int,
    payload: CommentIn,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    _photo_in_space(db, actor.space_id, photo_id)
    comment = Comment(
        photo_id=photo_id,
        participant_id=None if actor.is_leader else actor.participant_id,
        is_leader=actor.is_leader,
        content=payload.content,
        is_pinned=actor.is_leader,  # leader comments auto-pin
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return ok(_serialize_comment(comment, actor, False))


@router.put("/spaces/{space_id}/comments/{comment_id}")
def update_comment(
    space_id: str,
    comment_id: int,
    payload: CommentIn,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    comment = _get_space_comment(db, actor.space_id, comment_id)
    if not _can_modify(comment, actor):
        raise ApiError("只能编辑自己的批注", code=403, status_code=403)
    comment.content = payload.content
    db.commit()
    db.refresh(comment)
    liked = comment_id in my_comment_likes_set(db, [comment_id], actor.participant_id)
    return ok(_serialize_comment(comment, actor, liked))


@router.delete("/spaces/{space_id}/comments/{comment_id}")
def delete_comment(
    space_id: str,
    comment_id: int,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    comment = _get_space_comment(db, actor.space_id, comment_id)
    if not _can_modify(comment, actor):
        raise ApiError("只能删除自己的批注", code=403, status_code=403)
    db.delete(comment)
    db.commit()
    return ok({"deleted": comment_id})


def _can_modify(comment: Comment, actor: Actor) -> bool:
    if actor.is_leader:
        return comment.is_leader
    return (not comment.is_leader) and comment.participant_id == actor.participant_id


def _get_space_comment(db: Session, space_id: int, comment_id: int) -> Comment:
    comment = (
        db.query(Comment)
        .join(Photo, Photo.id == Comment.photo_id)
        .join(Category, Category.id == Photo.category_id)
        .filter(Comment.id == comment_id, Category.space_id == space_id)
        .first()
    )
    if not comment:
        raise ApiError("批注不存在", code=404, status_code=404)
    return comment


# ---------------- Comment likes ----------------
@router.post("/spaces/{space_id}/comments/{comment_id}/like")
def toggle_like(
    space_id: str,
    comment_id: int,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    comment = _get_space_comment(db, actor.space_id, comment_id)
    if actor.is_leader:
        raise ApiError("团长不参与赞同")

    existing = (
        db.query(CommentLike)
        .filter(CommentLike.comment_id == comment_id, CommentLike.participant_id == actor.participant_id)
        .first()
    )
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(CommentLike(comment_id=comment_id, participant_id=actor.participant_id))
        liked = True
    db.flush()

    count = db.query(func.count(CommentLike.id)).filter(CommentLike.comment_id == comment_id).scalar()
    comment.likes_count = int(count or 0)
    db.commit()
    return ok(LikeResp(comment_id=comment_id, likes_count=comment.likes_count, liked_by_me=liked).model_dump())


# ---------------- Favorites ----------------
@router.post("/spaces/{space_id}/photos/{photo_id}/favorite")
def toggle_favorite(
    space_id: str,
    photo_id: int,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    _photo_in_space(db, actor.space_id, photo_id)
    if actor.is_leader:
        raise ApiError("团长不参与喜欢标记")

    existing = (
        db.query(Favorite)
        .filter(Favorite.photo_id == photo_id, Favorite.participant_id == actor.participant_id)
        .first()
    )
    if existing:
        db.delete(existing)
        fav = False
    else:
        db.add(Favorite(photo_id=photo_id, participant_id=actor.participant_id))
        fav = True
    db.commit()
    return ok(FavoriteResp(photo_id=photo_id, favorite=fav).model_dump())
