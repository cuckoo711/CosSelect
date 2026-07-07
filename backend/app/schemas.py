from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---------- Space ----------
class SpaceCreateResp(BaseModel):
    space_id: int
    invite_code: str
    manage_key: str
    expire_time: datetime


class InviteCodeResp(BaseModel):
    space_id: int
    invite_code: str
    expire_time: datetime


class VerifyResp(BaseModel):
    valid: bool
    space_id: int


# ---------- Category ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    parent_id: int | None = None


class CategoryReorderItem(BaseModel):
    id: int
    sort_order: int


class CategoryReorder(BaseModel):
    items: list[CategoryReorderItem]


class CategoryOut(BaseModel):
    id: int
    space_id: int
    parent_id: int | None
    name: str
    sort_order: int
    photo_count: int = 0
    created_at: datetime
    children: list["CategoryOut"] = []


# ---------- Participant ----------
class ParticipantJoin(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("昵称不能为空")
        return v


class ParticipantResp(BaseModel):
    participant_id: int
    nickname: str
    token: str
    is_new: bool


# ---------- Photo ----------
class PhotoOut(BaseModel):
    id: int
    category_id: int
    original_name: str
    file_size: int
    upload_time: datetime
    thumbnail_url: str | None
    original_url: str
    avg_score: float
    rating_count: int
    comment_count: int
    my_score: float | None = None
    my_favorite: bool = False


class PhotoDetail(PhotoOut):
    comments: list["CommentOut"] = []


# ---------- Rating ----------
class RatingIn(BaseModel):
    score: float

    @field_validator("score")
    @classmethod
    def check_score(cls, v: float) -> float:
        if v < 0.5 or v > 5.0:
            raise ValueError("评分需在 0.5 到 5.0 之间")
        if round(v * 2) != v * 2:
            raise ValueError("评分步进为 0.5")
        return v


class RatingResp(BaseModel):
    photo_id: int
    avg_score: float
    rating_count: int
    my_score: float


# ---------- Comment ----------
class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("批注内容不能为空")
        return v


class CommentOut(BaseModel):
    id: int
    photo_id: int
    author: str
    is_leader: bool
    is_pinned: bool
    content: str
    likes_count: int
    liked_by_me: bool = False
    can_edit: bool = False
    created_at: datetime
    updated_at: datetime


class LikeResp(BaseModel):
    comment_id: int
    likes_count: int
    liked_by_me: bool


class FavoriteResp(BaseModel):
    photo_id: int
    favorite: bool


# ---------- Stats ----------
class StatsRow(BaseModel):
    photo_id: int
    original_name: str
    category_path: str
    thumbnail_url: str | None
    avg_score: float
    rating_count: int
    comment_count: int
    total_likes: int
    total_favorites: int


CategoryOut.model_rebuild()
PhotoDetail.model_rebuild()
